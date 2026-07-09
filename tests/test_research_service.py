"""Tests for the investment research report service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from parakeetnest.committee import (
    CommitteeOpinionStyle,
    CommitteePersona,
    CommitteeRole,
    PermanentCommitteeService,
)
from parakeetnest.config import get_settings
from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    EconomicRegimeContextSnapshot,
    FilingItem,
    FilingSnapshot,
    MacroSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
    NewsContext,
    NewsItem,
)
from parakeetnest.intelligence.risk.models import RiskAssessment, RiskLevel
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
)
from parakeetnest.watchlist import WatchlistInsight


AS_OF = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


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
    assert report.committee_consensus.final_action == "reduce"
    assert report.committee_consensus.confidence == "high"
    assert report.committee_consensus.rationale
    assert report.committee_consensus.todays_suggested_actions
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
        for label in ("Dongdong", "Xixi", "Youyou", "Committee:")
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
    assert report.committee_consensus.final_action == "watch"
    assert report.committee_consensus.confidence == "low"
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
    assert report.committee_consensus.final_action == "watch"
    assert report.committee_consensus.confidence == "low"
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


def test_committee_opinions_are_derived_from_persona_prompt_context() -> None:
    custom_dongdong = CommitteePersona(
        id="dongdong",
        display_name="Dongdong",
        role=CommitteeRole.CHIEF_GROWTH_OFFICER,
        role_title="Chief Growth Officer",
        responsibility="Use a custom growth responsibility.",
        default_viewpoint="Apply a custom upside lens.",
        risk_posture="Optimistic but bounded.",
        evidence_requirements=("Custom growth evidence.",),
        writing_style=CommitteeOpinionStyle.OPTIMISTIC_EVIDENCE_BASED,
        decision_biases_to_avoid=("Custom growth bias.",),
    )
    service = InvestmentResearchService(
        committee_service=PermanentCommitteeService(
            personas=(
                custom_dongdong,
                PermanentCommitteeService().get("xixi"),
                PermanentCommitteeService().get("youyou"),
            )
        )
    )

    report = service.generate_report(("NVDA",), generated_at=AS_OF)

    opinion = report.committee_opinions[0]
    assert opinion.persona_id == "dongdong"
    assert opinion.responsibility == "Use a custom growth responsibility."
    assert "Apply a custom upside lens." in opinion.viewpoint
    assert "upside case depends on evidence-backed catalysts" not in opinion.viewpoint


def test_all_committee_opinions_include_daily_report_reasoning_fields() -> None:
    service = InvestmentResearchService()

    report = service.generate_report(("NVDA",), generated_at=AS_OF)

    assert tuple(opinion.display_name for opinion in report.committee_opinions) == (
        "Dongdong",
        "Xixi",
        "Youyou",
    )
    for opinion in report.committee_opinions:
        assert opinion.stance in {"bullish", "neutral", "cautious"}
        assert opinion.reasoning_summary
        assert opinion.evidence_considered
        assert opinion.key_concern
        assert opinion.suggested_action
    assert report.committee_consensus.final_action
    assert report.committee_consensus.confidence
    assert report.committee_consensus.rationale
    assert report.committee_consensus.todays_suggested_actions


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
    assert "AAPL" in reviews["AAPL"].youyou_opinion
    assert "MSFT" not in reviews["AAPL"].youyou_opinion
    assert "MSFT" in reviews["MSFT"].dongdong_opinion
    assert "AAPL" not in reviews["MSFT"].dongdong_opinion
    assert "MSFT" in reviews["MSFT"].xixi_opinion
    assert "AAPL" not in reviews["MSFT"].xixi_opinion
    assert "MSFT" in reviews["MSFT"].youyou_opinion
    assert "AAPL" not in reviews["MSFT"].youyou_opinion
    assert "across 1 ticker(s)" in reviews["AAPL"].rationale
    assert "across 1 ticker(s)" in reviews["MSFT"].rationale
    assert "across 2 ticker(s)" in report.committee_consensus.rationale


def test_committee_opinions_keep_persona_specific_lenses(monkeypatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    service = InvestmentResearchService()

    try:
        report = service.generate_report(("NVDA",), generated_at=AS_OF)
        opinions = {
            opinion.display_name: opinion for opinion in report.committee_opinions
        }
    finally:
        get_settings.cache_clear()

    assert opinions["Dongdong"].stance == "neutral"
    assert "upside" in opinions["Dongdong"].reasoning_summary
    assert "Missing growth evidence" in opinions["Dongdong"].reasoning_summary
    assert "catalyst" in opinions["Dongdong"].suggested_action.lower()
    assert "fundamentals" in opinions["Xixi"].reasoning_summary
    assert "valuation" in opinions["Xixi"].reasoning_summary
    assert "Missing fundamental evidence" in opinions["Xixi"].reasoning_summary
    assert "valuation" in opinions["Xixi"].suggested_action
    assert opinions["Youyou"].stance == "cautious"
    assert "capital preservation" in opinions["Youyou"].reasoning_summary
    assert "position sizing" in opinions["Youyou"].reasoning_summary
    assert "Missing risk evidence" in opinions["Youyou"].reasoning_summary
    assert "advisory only" in opinions["Youyou"].suggested_action


def test_report_facing_committee_text_can_be_chinese(monkeypatch) -> None:
    monkeypatch.setenv("PARAKEET_REPORT_LANGUAGE", "zh")
    get_settings.cache_clear()
    service = InvestmentResearchService()

    report = service.generate_report(("NVDA",), generated_at=AS_OF)

    assert report.tickers() == ("NVDA",)
    assert "上行空间" in report.committee_opinions[0].reasoning_summary
    assert "委员会" in report.committee_consensus.rationale
    assert "NVDA" in report.committee_consensus.todays_suggested_actions[0]
    get_settings.cache_clear()


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
