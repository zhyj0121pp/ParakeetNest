"""Tests for the investment research report service."""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from parakeetnest.config import get_settings
from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    EconomicRegimeContextSnapshot,
    FilingItem,
    FilingSnapshot,
    FinancialStatementItem,
    FinancialStatementSnapshot,
    MacroSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
    NewsContext,
    NewsItem,
)
from parakeetnest.intelligence.risk.models import RiskAssessment, RiskLevel
from parakeetnest.llm import LLMRequest, LLMResponse, MockLLMProvider
from parakeetnest.portfolio import (
    PortfolioCashBalance,
    PortfolioHolding,
    PortfolioSnapshot,
)
from parakeetnest.research import service as research_service
from parakeetnest.research import (
    InvestmentResearchService,
    ReportMode,
    inspect_committee_fact_inputs,
    render_investment_research_report_interactive_html,
)
from parakeetnest.watchlist import WatchlistInsight


AS_OF = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


def test_yahoo_financial_facts_flow_into_research_prompt_evidence_and_html() -> None:
    class FinancialPublicContextService:
        def build_context(self, request: ContextRequest) -> MeetingContext:
            return MeetingContext(
                request=request,
                metadata=ContextMetadata(sources=("financial_statements",)),
                financials=FinancialStatementSnapshot(
                    source="financial_statements",
                    fetched_at=AS_OF,
                    items=(
                        FinancialStatementItem(
                            symbol="NVDA",
                            period_type="annual",
                            source="yahoo",
                            revenue=130_000_000_000,
                            gross_profit=98_000_000_000,
                            operating_income=75_000_000_000,
                            net_income=70_000_000_000,
                            eps=3.10,
                            cash=43_000_000_000,
                            total_debt=10_000_000_000,
                            operating_cash_flow=64_000_000_000,
                            free_cash_flow=58_000_000_000,
                            fiscal_year=2026,
                            currency="USD",
                        ),
                    ),
                ),
            )

    report = InvestmentResearchService(
        public_context_service=FinancialPublicContextService()
    ).generate_report(("NVDA",), generated_at=AS_OF)

    ticker_report = report.ticker_reports[0]
    assert ticker_report.financial_facts
    assert "Yahoo/financials: NVDA" in ticker_report.financial_facts[0]
    assert "revenue=130.00B USD" in ticker_report.financial_facts[0]
    assert "eps=3.10" in ticker_report.financial_facts[0]
    assert "financials: public financial statement facts" in (
        ticker_report.source_summaries
    )
    assert ticker_report.financial_facts[0] in report.position_committee_reviews[0].evidence
    assert "financial_facts:" in inspect_committee_fact_inputs(report)

    html = render_investment_research_report_interactive_html(report, language="en")
    assert "Financial statements" in html
    assert "Yahoo/financials: NVDA" in html


class FakePortfolioService:
    def __init__(self, snapshot: PortfolioSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[str] = []

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        self.calls.append(account_id)
        return self.snapshot


class FakeWatchlistService:
    def __init__(self, insights: dict[str, WatchlistInsight]) -> None:
        self.insights = insights
        self.calls: list[str] = []

    def build_insight(self, symbol: str) -> WatchlistInsight:
        self.calls.append(symbol)
        if symbol not in self.insights:
            raise ValueError(f"missing {symbol}")
        return self.insights[symbol]


class FakeIntelligenceContext:
    def __init__(self) -> None:
        self.risk = RiskAssessment(
            overall_level=RiskLevel.MODERATE,
            overall_score=0.42,
            summary="Moderate market risk supports measured sizing.",
        )


class FakeIntelligenceService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, date | None]] = []

    def build_context(
        self,
        *,
        as_of_date: date | None = None,
        universe: str = "US",
        symbol: str = "SPY",
    ) -> FakeIntelligenceContext:
        self.calls.append((symbol, as_of_date))
        return FakeIntelligenceContext()


class FakePublicContextService:
    def __init__(self) -> None:
        self.calls: list[ContextRequest] = []

    def build_context(self, request: ContextRequest) -> MeetingContext:
        self.calls.append(request)
        return MeetingContext(
            request=request,
            metadata=ContextMetadata(sources=("market_data", "sec_filings", "macro")),
            market=MarketSnapshot(
                source="market_data",
                points=(
                    MarketDataPoint(
                        symbol="NVDA",
                        source="market_data",
                        price=204.12,
                        daily_change_percent=4.2,
                        volume=145_000_000,
                    ),
                ),
            ),
            filings=FilingSnapshot(
                source="sec_filings",
                items=(
                    FilingItem(
                        symbol="NVDA",
                        filing_type="10-Q",
                        source="edgar",
                        accession_number="000-test",
                        summary="10-Q",
                    ),
                ),
            ),
            news=NewsContext(
                source="news",
                items=(
                    NewsItem(
                        symbol="NVDA",
                        title="Nvidia supplier demand expands",
                        source="Yahoo Finance",
                        url="https://finance.yahoo.com/news/nvda-demand",
                        published_at=AS_OF,
                    ),
                    NewsItem(
                        symbol="AAPL",
                        title="Apple services revenue rises",
                        source="Yahoo Finance",
                        url="https://finance.yahoo.com/news/aapl-services",
                        published_at=AS_OF,
                    ),
                    NewsItem(
                        symbol="MSFT",
                        title="Microsoft cloud backlog grows",
                        source="Yahoo Finance",
                        url="https://finance.yahoo.com/news/msft-cloud",
                        published_at=AS_OF,
                    ),
                ),
            ),
            macro=MacroSnapshot(
                source="macro",
                indicators=("Interest Rates: Fed Funds 3.5 as of 2026-07-01",),
            ),
            economic_regime=EconomicRegimeContextSnapshot(
                source="economic_regime",
                regime="expansion",
                confidence="medium",
            ),
        )


class FakeDifferentiatedPublicContextService:
    def build_context(self, request: ContextRequest) -> MeetingContext:
        return MeetingContext(
            request=request,
            metadata=ContextMetadata(sources=("market_data", "sec_filings", "macro")),
            market=MarketSnapshot(
                source="market_data",
                points=(
                    MarketDataPoint(
                        symbol="NVDA",
                        source="market_data",
                        price=204.12,
                        daily_change=8.25,
                        daily_change_percent=4.20,
                        volume=145_000_000,
                        market_cap=5_000_000_000_000,
                        pe_ratio=52.4,
                    ),
                    SimpleNamespace(
                        symbol="AAPL",
                        source="market_data",
                        price=212.43,
                        daily_change=-1.10,
                        daily_change_percent=-0.52,
                        volume=48_000_000,
                        market_cap=3_200_000_000_000,
                        pe_ratio=31.2,
                        sector="Technology",
                        industry="Consumer Electronics",
                        forward_pe=28.7,
                        beta=1.18,
                        enterprise_value=3_300_000_000_000,
                        revenue_ttm=410_000_000_000,
                        ev_to_sales=8.05,
                        observed_at=None,
                    ),
                    MarketDataPoint(
                        symbol="MSFT",
                        source="market_data",
                        price=498.84,
                        daily_change=2.75,
                        daily_change_percent=0.55,
                        volume=7_500_000,
                        market_cap=3_700_000_000_000,
                        pe_ratio=38.9,
                    ),
                ),
            ),
            filings=FilingSnapshot(
                source="sec_filings",
                items=(
                    FilingItem(
                        symbol="NVDA",
                        filing_type="10-Q",
                        source="edgar",
                        accession_number="nvda-10q",
                        summary="NVDA quarterly filing",
                    ),
                    FilingItem(
                        symbol="AAPL",
                        filing_type="10-K",
                        source="edgar",
                        accession_number="aapl-10k",
                        summary="AAPL annual filing",
                    ),
                    FilingItem(
                        symbol="MSFT",
                        filing_type="8-K",
                        source="edgar",
                        accession_number="msft-8k",
                        summary="MSFT current report",
                    ),
                ),
            ),
            news=NewsContext(
                source="news",
                items=(
                    NewsItem(
                        symbol="NVDA",
                        title="Nvidia supplier demand expands",
                        source="Yahoo Finance",
                        url="https://finance.yahoo.com/news/nvda-demand",
                        published_at=AS_OF,
                    ),
                    NewsItem(
                        symbol="AAPL",
                        title="Apple services revenue rises",
                        source="Yahoo Finance",
                        url="https://finance.yahoo.com/news/aapl-services",
                        published_at=AS_OF,
                    ),
                    NewsItem(
                        symbol="MSFT",
                        title="Microsoft cloud backlog grows",
                        source="Yahoo Finance",
                        url="https://finance.yahoo.com/news/msft-cloud",
                        published_at=AS_OF,
                    ),
                ),
            ),
            macro=MacroSnapshot(
                source="macro",
                indicators=(
                    "Interest Rates: Fed Funds 3.5 as of 2026-07-01",
                    "Inflation: CPI 2.4 as of 2026-07-01",
                ),
                summary="Macro facts are market-wide, not ticker-specific.",
            ),
            economic_regime=EconomicRegimeContextSnapshot(
                source="economic_regime",
                regime="expansion",
                confidence="medium",
                indicators=("Growth: payrolls positive",),
            ),
        )


def _portfolio_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id="main",
        as_of=AS_OF,
        holdings=(
            PortfolioHolding(
                symbol="NVDA",
                name="Nvidia",
                quantity=10,
                average_cost=90,
                current_price=120,
                market_value=1200,
            ),
        ),
    )


def _three_ticker_portfolio_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id="main",
        as_of=AS_OF,
        cash_balances=(PortfolioCashBalance(amount=500),),
        total_equity=10_000,
        holdings=(
            PortfolioHolding(
                symbol="NVDA",
                name="Nvidia",
                quantity=10,
                average_cost=90,
                current_price=204.12,
                market_value=2_041.20,
                sector="Technology",
            ),
            PortfolioHolding(
                symbol="AAPL",
                name="Apple",
                quantity=8,
                average_cost=180,
                current_price=212.43,
                market_value=1_699.44,
                sector="Technology",
            ),
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                quantity=3,
                average_cost=400,
                current_price=498.84,
                market_value=1_496.52,
                sector="Technology",
            ),
        ),
    )


def test_generate_report_combines_portfolio_watchlist_and_intelligence() -> None:
    portfolio = FakePortfolioService(_portfolio_snapshot())
    watchlist = FakeWatchlistService(
        {
            "NVDA": WatchlistInsight(
                symbol="NVDA",
                summary="AI accelerator demand remains a key thesis.",
                bullish_factors=("Datacenter demand.",),
                bearish_factors=("Export controls.",),
                recommended_action="continue monitoring",
            )
        }
    )
    intelligence = FakeIntelligenceService()
    public_context = FakePublicContextService()
    service = InvestmentResearchService(
        portfolio_service=portfolio,
        public_context_service=public_context,
        watchlist_service=watchlist,
        intelligence_service=intelligence,
    )

    report = service.generate_report(
        [" nvda ", "NVDA"],
        account_id="main",
        as_of_date=date(2026, 7, 1),
        generated_at=AS_OF,
    )

    ticker_report = report.ticker_reports[0]
    assert report.tickers() == ("NVDA",)
    assert report.portfolio_context is not None
    assert report.portfolio_context.total_value == 1200
    assert report.portfolio_context.positions[0].symbol == "NVDA"
    assert report.portfolio_context.allocation_by_symbol[0].percent == 1.0
    assert ticker_report.summary == (
        "NVDA is both a portfolio holding and watchlist research item."
    )
    assert "Datacenter demand." in ticker_report.bull_case
    assert "Export controls." in ticker_report.bear_case
    assert not hasattr(ticker_report, "recommendation")
    assert report.position_committee_reviews[0].recommendation
    assert report.position_committee_reviews[0].confidence
    assert report.position_committee_reviews[0].rationale
    assert "portfolio: current holding facts" in ticker_report.source_summaries
    assert "watchlist: user thesis and notes" in (
        ticker_report.source_summaries
    )
    assert "market_context: factual market context" in (
        ticker_report.source_summaries
    )
    assert "market_data: public market facts" in ticker_report.source_summaries
    assert "sec_filings: public company filings" in ticker_report.source_summaries
    assert "macro: public macro facts" in ticker_report.source_summaries
    assert "portfolio: privacy-safe bucketed context" in (
        ticker_report.source_summaries
    )
    assert ticker_report.public_market_facts
    assert ticker_report.company_facts
    assert ticker_report.macro_facts
    assert ticker_report.portfolio_summary is not None
    assert ticker_report.position_context is not None
    assert ticker_report.position_context.privacy_level == "bucketed"
    review = report.position_committee_reviews[0]
    assert any(item.startswith("portfolio:") for item in review.evidence)
    assert any(item.startswith("watchlist:") for item in review.evidence)
    assert any(item.startswith("market_context:") for item in review.evidence)
    assert not any(item.startswith("investment_intelligence:") for item in review.evidence)
    assert not any("aggregate intelligence:" in item for item in review.evidence)
    assert not any(item.startswith(("bull_case:", "bear_case:")) for item in review.evidence)
    assert not any(
        label in item
        for item in review.evidence
        for label in ("Dongdong", "Xixi", "Yoyo", "Committee:")
    )
    assert "Risk is moderate and manageable" not in " ".join(review.evidence)
    assert "yahoo/market_data" in " ".join(review.evidence).lower()
    report_text = _report_text(report)
    assert "investment_intelligence" not in report_text
    assert "market_context" in report_text
    assert "Yahoo/market_data" in report_text
    assert "SEC EDGAR" in report_text
    assert "FRED/macro" in report_text
    forbidden_private_terms = (
        "quantity",
        "market_value",
            "cost_basis",
            "average_cost",
            "account_id",
            "742192826",
        )
    assert all(term not in " ".join(review.evidence) for term in forbidden_private_terms)
    assert portfolio.calls == ["main"]
    assert watchlist.calls == ["NVDA"]
    assert intelligence.calls == [("NVDA", date(2026, 7, 1))]
    assert public_context.calls
    assert public_context.calls[0].include_portfolio is False


def test_ticker_fact_inputs_are_differentiated_and_privacy_safe() -> None:
    service = InvestmentResearchService(
        portfolio_service=FakePortfolioService(_three_ticker_portfolio_snapshot()),
        public_context_service=FakeDifferentiatedPublicContextService(),
    )

    report = service.generate_report(
        ("NVDA", "AAPL", "MSFT"),
        account_id="main",
        generated_at=AS_OF,
    )
    by_ticker = {
        ticker_report.ticker: ticker_report
        for ticker_report in report.ticker_reports
    }

    assert (
        by_ticker["NVDA"].public_market_facts
        != by_ticker["AAPL"].public_market_facts
    )
    assert (
        by_ticker["AAPL"].public_market_facts
        != by_ticker["MSFT"].public_market_facts
    )
    assert any("price=204.12" in fact for fact in by_ticker["NVDA"].public_market_facts)
    assert any(
        "daily_change=8.25" in fact
        for fact in by_ticker["NVDA"].public_market_facts
    )
    assert any(
        "daily_change_percent=4.20" in fact
        for fact in by_ticker["NVDA"].public_market_facts
    )
    assert any(
        "volume_bucket=very_high" in fact
        for fact in by_ticker["NVDA"].public_market_facts
    )
    assert any(
        "market_cap=mega_cap" in fact
        for fact in by_ticker["NVDA"].public_market_facts
    )
    assert any(
        "pe_ratio=52.40" in fact
        for fact in by_ticker["NVDA"].public_market_facts
    )
    assert any(
        "sector=Technology" in fact
        for fact in by_ticker["AAPL"].profile_facts
    )
    assert any(
        "industry=Consumer Electronics" in fact
        for fact in by_ticker["AAPL"].profile_facts
    )
    assert any(
        "forward_pe=28.70" in fact
        for fact in by_ticker["AAPL"].valuation_facts
    )
    assert any("beta=1.18" in fact for fact in by_ticker["AAPL"].profile_facts)
    assert any("ev_to_sales=8.05" in fact for fact in by_ticker["AAPL"].valuation_facts)
    assert by_ticker["AAPL"].fact_interpretation.valuation_label == "expensive"
    assert "EV/Sales 8.05" in by_ticker["AAPL"].fact_interpretation.valuation_summary
    assert "beta=1.18" in by_ticker["AAPL"].fact_interpretation.profile_summary
    assert any(
        fact.startswith("Yahoo/valuation: AAPL")
        for fact in by_ticker["AAPL"].valuation_facts
    )
    assert not any(
        "sector=" in fact or "industry=" in fact or "beta=" in fact
        for fact in by_ticker["MSFT"].profile_facts
    )
    assert any(
        "trailing_pe=38.90" in fact
        for fact in by_ticker["MSFT"].valuation_facts
    )
    assert by_ticker["MSFT"].fact_interpretation.valuation_label == "fair"
    assert not any(
        "ev_to_sales" in fact for fact in by_ticker["MSFT"].valuation_facts
    )
    all_public_facts = (
        by_ticker["AAPL"].public_market_facts
        + by_ticker["AAPL"].profile_facts
        + by_ticker["AAPL"].valuation_facts
        + by_ticker["AAPL"].news_facts
        + by_ticker["AAPL"].company_facts
    )
    assert not any("Robinhood" in fact or "robinhood" in fact for fact in all_public_facts)
    assert any(
        "volume_bucket=moderate" in fact
        for fact in by_ticker["MSFT"].public_market_facts
    )
    assert by_ticker["NVDA"].news_facts != by_ticker["AAPL"].news_facts
    assert any(
        fact.startswith("Yahoo/news: NVDA")
        for fact in by_ticker["NVDA"].news_facts
    )
    assert any(
        "title=Nvidia supplier demand expands" in fact
        for fact in by_ticker["NVDA"].news_facts
    )
    assert any(
        "publisher=Yahoo Finance" in fact
        for fact in by_ticker["NVDA"].news_facts
    )
    assert any(
        "url=https://finance.yahoo.com/news/nvda-demand" in fact
        for fact in by_ticker["NVDA"].news_facts
    )

    assert by_ticker["NVDA"].company_facts == (
        "SEC EDGAR: NVDA 10-Q, accession_number=nvda-10q, "
        "summary=NVDA quarterly filing",
    )
    assert by_ticker["AAPL"].company_facts == (
        "SEC EDGAR: AAPL 10-K, accession_number=aapl-10k, summary=AAPL annual filing",
    )
    assert by_ticker["MSFT"].company_facts == (
        "SEC EDGAR: MSFT 8-K, accession_number=msft-8k, summary=MSFT current report",
    )

    macro_facts = by_ticker["NVDA"].macro_facts
    assert macro_facts == by_ticker["AAPL"].macro_facts == by_ticker["MSFT"].macro_facts
    assert all(
        fact.startswith(("FRED/macro", "FRED/economic_regime"))
        for fact in macro_facts
    )

    position_reviews = {
        review.ticker: review for review in report.position_committee_reviews
    }
    assert "Valuation label=expensive" in position_reviews["AAPL"].xixi_opinion
    assert "beta=1.18" in position_reviews["AAPL"].xixi_opinion
    actions = {review.recommendation for review in report.position_committee_reviews}
    assert len(actions) > 1

    for ticker_report in report.ticker_reports:
        assert ticker_report.position_context is not None
        assert ticker_report.position_context.privacy_level == "bucketed"
        assert ticker_report.position_context.position_size_bucket in {
            "small",
            "medium",
            "large",
            "very_large",
        }

    inspection = inspect_committee_fact_inputs(report)
    assert "public_market_facts:" in inspection
    assert "news_facts:" in inspection
    assert "company_facts:" in inspection
    assert "macro_facts:" in inspection
    assert "market_context_facts:" in inspection
    assert "position_context:" in inspection
    assert "source_summaries:" in inspection
    assert "ticker: NVDA" in inspection
    assert "ticker: AAPL" in inspection
    assert "ticker: MSFT" in inspection
    assert "privacy_level=bucketed" in inspection
    forbidden_private_terms = (
        "quantity",
        "average_cost",
        "cost_basis",
        "market_value",
        "account_id",
    )
    assert all(term not in inspection for term in forbidden_private_terms)


def test_generate_report_supports_watchlist_only_tickers() -> None:
    watchlist = FakeWatchlistService(
        {
            "AAPL": WatchlistInsight(
                symbol="AAPL",
                summary="Services mix can support margins.",
                bullish_factors=("Services growth.",),
                bearish_factors=("China demand risk.",),
            )
        }
    )
    service = InvestmentResearchService(watchlist_service=watchlist)

    report = service.generate_report(("AAPL",), generated_at=AS_OF)

    ticker_report = report.ticker_reports[0]
    assert not hasattr(ticker_report, "recommendation")
    assert report.position_committee_reviews[0].recommendation == "watch"
    assert report.position_committee_reviews[0].confidence == "low"
    assert ticker_report.risks[0].summary == "China demand risk."
    assert ticker_report.catalysts[0].summary == "Services growth."


def test_generate_report_uses_explicit_research_gap_when_no_context_connected() -> None:
    service = InvestmentResearchService()

    report = service.generate_report(
        ("TSLA",),
        generated_at=AS_OF,
        mode=ReportMode.EVENING,
    )

    ticker_report = report.ticker_reports[0]
    assert ticker_report.summary == (
        "TSLA is included for research, but connected context is limited."
    )
    assert not hasattr(ticker_report, "recommendation")
    assert report.position_committee_reviews[0].recommendation == "watch"
    assert report.position_committee_reviews[0].confidence == "low"
    assert report.mode is ReportMode.EVENING
    assert report.title == "Evening Investment Review"
    assert ticker_report.findings[0].source == "research_service"
    assert ticker_report.findings[0].summary == "No connected factual context available."
    assert ticker_report.risks[0].summary == "No connected factual context available."
    assert ticker_report.catalysts[0].summary == "No connected factual context available."
    assert ticker_report.bull_case == ("No connected factual context available.",)
    assert ticker_report.bear_case == ("No connected factual context available.",)
    assert ticker_report.evidence_notes == ()
    assert "No portfolio service connected." in report.evidence_notes
    assert "No market context service connected." in report.evidence_notes


def test_market_context_helpers_replace_intelligence_and_risk_summaries() -> None:
    context = FakeIntelligenceContext()

    assert not hasattr(research_service, "_intelligence_summary")
    assert not hasattr(research_service, "_risk_summary")
    assert research_service._market_context_summary(context) == (
        "Market context facts: risk level=moderate; risk score=0.42"
    )
    assert research_service._market_context_risk_facts(context) == (
        "risk level=moderate",
        "risk score=0.42",
    )


def test_market_context_does_not_emit_generic_judgment_phrases() -> None:
    service = InvestmentResearchService(intelligence_service=FakeIntelligenceService())

    report = service.generate_report(("NVDA",), generated_at=AS_OF)

    report_text = _report_text(report)
    forbidden = (
        "Market intelligence context available",
        "Aggregate risk is",
        "Risk is moderate and manageable",
        "aggregate intelligence",
        "investment_intelligence",
    )
    for phrase in forbidden:
        assert phrase not in report_text
    assert "market_context: factual market context" in report_text


def test_generate_report_builds_per_position_committee_reviews(monkeypatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    service = InvestmentResearchService()

    try:
        report = service.generate_report(("AAPL", "MSFT"), generated_at=AS_OF)
    finally:
        get_settings.cache_clear()

    assert tuple(review.ticker for review in report.position_committee_reviews) == (
        "AAPL",
        "MSFT",
    )
    reviews = {
        review.ticker: review
        for review in report.position_committee_reviews
    }
    assert "AAPL" in reviews["AAPL"].dongdong_opinion
    assert "MSFT" not in reviews["AAPL"].dongdong_opinion
    assert "AAPL" in reviews["AAPL"].xixi_opinion
    assert "MSFT" not in reviews["AAPL"].xixi_opinion
    assert "AAPL" in reviews["AAPL"].yoyo_opinion
    assert "MSFT" not in reviews["AAPL"].yoyo_opinion
    assert "MSFT" in reviews["MSFT"].dongdong_opinion
    assert "AAPL" not in reviews["MSFT"].dongdong_opinion
    assert "MSFT" in reviews["MSFT"].xixi_opinion
    assert "AAPL" not in reviews["MSFT"].xixi_opinion
    assert "MSFT" in reviews["MSFT"].yoyo_opinion
    assert "AAPL" not in reviews["MSFT"].yoyo_opinion
    assert "across 1 ticker(s)" in reviews["AAPL"].rationale
    assert "across 1 ticker(s)" in reviews["MSFT"].rationale


def test_report_facing_committee_text_can_be_chinese(monkeypatch) -> None:
    monkeypatch.setenv("PARAKEET_REPORT_LANGUAGE", "zh")
    get_settings.cache_clear()
    service = InvestmentResearchService()

    report = service.generate_report(("NVDA",), generated_at=AS_OF)

    assert report.tickers() == ("NVDA",)
    assert "上行空间" in report.position_committee_reviews[0].dongdong_opinion
    assert "委员会" in report.position_committee_reviews[0].rationale
    get_settings.cache_clear()


def test_llm_persona_discussions_are_produced_from_prompts() -> None:
    llm = ConcurrentRecordingLLMProvider()
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    report = service.generate_report(("NVDA",), generated_at=AS_OF)

    review = report.position_committee_reviews[0]
    assert review.dongdong_opinion.startswith(
        "Dongdong LLM action=watch"
    )
    assert review.xixi_opinion.startswith(
        "Xixi LLM action=hold"
    )
    assert review.yoyo_opinion.startswith(
        "Yoyo LLM action=reduce"
    )
    assert review.rationale == (
        "Chairman LLM synthesizes final advisory recommendation."
    )
    assert len(llm.requests) == 4
    dongdong_request = next(
        request
        for request in llm.requests
        if request.metadata["agent_name"] == "Dongdong"
    )
    assert dongdong_request.metadata["task"] == "daily_report_persona_opinion"
    assert "You are Dongdong" in dongdong_request.prompt
    assert (
        "Return only a JSON object matching CommitteeOpinion"
        in dongdong_request.prompt
    )
    assert "viewpoint must be 2-4 short sentences" in dongdong_request.prompt
    assert dongdong_request.max_completion_tokens == 350
    chairman_request = llm.requests[-1]
    assert chairman_request.metadata["task"] == "daily_report_chairman_synthesis"
    assert "Persona Opinions" in chairman_request.prompt
    assert "Dongdong" in chairman_request.prompt
    assert "Xixi" in chairman_request.prompt
    assert "Yoyo" in chairman_request.prompt
    assert "Ticker Evidence" not in chairman_request.prompt
    assert "PRE-COMMITTEE ANALYSIS" not in chairman_request.prompt
    assert "Yahoo/profile" not in chairman_request.prompt
    assert "forward_pe=" not in chairman_request.prompt
    assert "ev_to_sales=" not in chairman_request.prompt


def test_llm_prompts_include_yahoo_profile_and_valuation_facts() -> None:
    llm = MockLLMProvider(responses=_llm_committee_responses("AAPL"))
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    service.generate_report(("AAPL",), generated_at=AS_OF)

    persona_prompt = next(
        request.prompt
        for request in llm.requests
        if request.metadata.get("agent_name") == "Xixi"
    )
    assert "Yahoo / profile facts:" in persona_prompt
    assert "Yahoo/profile: AAPL" in persona_prompt
    assert "sector=Technology" in persona_prompt
    assert "industry=Consumer Electronics" in persona_prompt
    assert "Yahoo / valuation facts:" in persona_prompt
    assert "Yahoo/valuation: AAPL" in persona_prompt
    assert "forward_pe=28.70" in persona_prompt
    assert "ev_to_sales=8.05" in persona_prompt


def test_persona_prompts_route_only_relevant_fact_sections() -> None:
    llm = MockLLMProvider(responses=_llm_committee_responses("AAPL"))
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    service.generate_report(("AAPL",), generated_at=AS_OF)

    prompts = {
        request.metadata.get("agent_name"): request.prompt
        for request in llm.requests
        if request.metadata.get("task") == "daily_report_persona_opinion"
    }
    assert "Yahoo/news: AAPL" in prompts["Dongdong"]
    assert "SEC EDGAR: AAPL" not in prompts["Dongdong"]
    assert "FRED/macro" not in prompts["Dongdong"]
    assert "Yahoo/valuation: AAPL" in prompts["Xixi"]
    assert "SEC EDGAR: AAPL" in prompts["Xixi"]
    assert "Yahoo/news: AAPL" not in prompts["Xixi"]
    assert "FRED/macro" not in prompts["Xixi"]
    assert "Yahoo/valuation: AAPL" in prompts["Yoyo"]
    assert "FRED/macro" in prompts["Yoyo"]


def test_unscoped_news_is_not_injected_into_ticker_facts() -> None:
    context = MeetingContext(
        request=ContextRequest(question="Research AAPL", symbols=("AAPL",)),
        metadata=ContextMetadata(sources=("news",)),
        news=NewsContext(
            source="news",
            items=(
                NewsItem(
                    symbol=None,
                    title="Unscoped market headline",
                    source="Yahoo Finance",
                ),
                NewsItem(
                    symbol="AAPL",
                    title="Apple services revenue rises",
                    source="Yahoo Finance",
                ),
            ),
        ),
    )

    facts = research_service._news_facts(context, "AAPL")

    assert len(facts) == 1
    assert "Apple services revenue rises" in facts[0]
    assert "Unscoped market headline" not in facts[0]


def test_llm_prompts_separate_pre_committee_analysis_from_factual_evidence() -> None:
    llm = MockLLMProvider(responses=_llm_committee_responses("AAPL"))
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    service.generate_report(("AAPL",), generated_at=AS_OF)

    persona_prompt = next(
        request.prompt
        for request in llm.requests
        if request.metadata.get("agent_name") == "Xixi"
    )
    facts_index = persona_prompt.index("PUBLIC FACTS")
    analysis_index = persona_prompt.index("PRE-COMMITTEE ANALYSIS")
    assert facts_index < analysis_index
    assert "Deterministic ResearchFactInterpretation, not raw factual evidence" in (
        persona_prompt
    )
    assert "Yahoo/valuation: AAPL" in persona_prompt[facts_index:analysis_index]
    assert "valuation_assessment=expensive" in persona_prompt[analysis_index:]
    assert "EV/Sales 8.05" not in persona_prompt[analysis_index:]
    assert "valuation_assessment=expensive" not in (
        persona_prompt[facts_index:analysis_index]
    )


def test_invalid_llm_output_falls_back_to_deterministic_judgment() -> None:
    llm = MockLLMProvider(responses=("{not valid json",))
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    report = service.generate_report(("AAPL",), generated_at=AS_OF)

    review = report.position_committee_reviews[0]
    assert "LLM action" not in review.dongdong_opinion
    assert review.evidence
    assert review.recommendation
    assert review.confidence


def test_llm_prompts_are_scoped_to_one_ticker() -> None:
    llm = ConcurrentRecordingLLMProvider()
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    service.generate_report(("AAPL", "MSFT"), generated_at=AS_OF)

    scoped_requests = llm.requests
    llm_tickers = {request.metadata["tickers"] for request in scoped_requests}
    assert llm_tickers == {"AAPL", "MSFT"}
    assert "AAPL,MSFT" not in llm_tickers
    aapl_prompts = [
        request.prompt
        for request in scoped_requests
        if request.metadata["tickers"] == "AAPL"
    ]
    msft_prompts = [
        request.prompt
        for request in scoped_requests
        if request.metadata["tickers"] == "MSFT"
    ]
    assert aapl_prompts
    assert msft_prompts
    assert all("AAPL" in prompt for prompt in aapl_prompts)
    assert all("MSFT" not in prompt for prompt in aapl_prompts)
    assert all("MSFT" in prompt for prompt in msft_prompts)
    assert all("AAPL" not in prompt for prompt in msft_prompts)
    assert len(llm.requests) == 8
    assert not any(
        request.metadata["task"] == "daily_report_final_synthesis"
        for request in llm.requests
    )


def test_same_ticker_persona_llm_calls_run_concurrently() -> None:
    llm = ConcurrentRecordingLLMProvider()
    service = InvestmentResearchService(
        public_context_service=FakeDifferentiatedPublicContextService(),
        llm_provider=llm,
    )

    report = service.generate_report(("AAPL",), generated_at=AS_OF)

    assert report.position_committee_reviews
    assert report.position_committee_reviews[0].dongdong_opinion.startswith(
        "Dongdong LLM action=watch"
    )
    assert llm.max_active >= 2


def test_research_package_has_no_broker_or_trading_execution_logic() -> None:
    research_dir = Path(__file__).parents[1] / "src" / "parakeetnest" / "research"
    source = "\n".join(path.read_text() for path in research_dir.glob("*.py")).lower()

    forbidden_terms = (
        "broker",
        "brokerage",
        "place_order",
        "execute_trade",
        "automatic_trading",
        "rebalance_account",
    )
    for term in forbidden_terms:
        assert term not in source


def _report_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_report_text(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return " ".join(_report_text(item) for item in value)
    if hasattr(value, "__dict__"):
        return _report_text(vars(value))
    return str(value)


class ConcurrentRecordingLLMProvider:
    name = "concurrent"
    default_model = "concurrent-llm"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def complete(self, request: LLMRequest) -> LLMResponse:
        with self._lock:
            self.requests.append(request)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        try:
            if request.metadata.get("task") == "daily_report_chairman_synthesis":
                content = _chairman_json(str(request.metadata["tickers"]))
            else:
                member_name = str(request.metadata["agent_name"])
                role = str(request.metadata["role"])
                symbol = str(request.metadata["tickers"])
                action = {
                    "Dongdong": "watch",
                    "Xixi": "hold",
                    "Yoyo": "reduce",
                }.get(member_name, "watch")
                content = _committee_opinion_json(member_name, role, symbol, action)
            return LLMResponse(
                content=content,
                model=request.model,
                provider_name=self.name,
            )
        finally:
            with self._lock:
                self.active -= 1


def _llm_committee_responses(symbol: str) -> tuple[str, ...]:
    return (
        _committee_opinion_json("Dongdong", "Chief Growth Officer", symbol, "watch"),
        _committee_opinion_json("Xixi", "Chief Investment Analyst", symbol, "hold"),
        _committee_opinion_json("Yoyo", "Chief Risk Officer", symbol, "reduce"),
        _chairman_json(symbol),
    )


def _committee_opinion_json(
    member_name: str,
    role: str,
    symbol: str,
    action: str,
) -> str:
    return json.dumps(
        {
            "member_name": member_name,
            "role": role,
            "symbol": symbol,
            "viewpoint": (
                f"{member_name} LLM action={action}; confidence=medium; "
                "horizon=3_months; evidence=supplied Yahoo facts; "
                "risks=valuation risk; catalysts=research catalyst."
            ),
            "confidence": "medium",
            "evidence": [
                {
                    "summary": "supplied Yahoo facts",
                    "source": "Yahoo/valuation",
                    "observed_at": None,
                }
            ],
            "risks": ["valuation risk"],
            "catalysts": ["research catalyst"],
        },
        sort_keys=True,
    )


def _chairman_json(symbol: str) -> str:
    return json.dumps(
        {
            "symbol": symbol,
            "action": "watch",
            "confidence": "medium",
            "horizon": "3_months",
            "rationale": "Chairman LLM synthesizes final advisory recommendation.",
            "evidence": [
                {
                    "summary": "supplied source-labeled facts",
                    "source": "committee_prompt",
                    "observed_at": None,
                }
            ],
            "risks": ["valuation risk"],
            "catalysts": ["research catalyst"],
            "data_confidence": "medium",
        },
        sort_keys=True,
    )
