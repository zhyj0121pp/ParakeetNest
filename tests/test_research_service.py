"""Tests for the investment research report service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from parakeetnest.committee import (
    CommitteeOpinionStyle,
    CommitteePersona,
    CommitteeRole,
    PermanentCommitteeService,
)
from parakeetnest.intelligence.risk.models import RiskAssessment, RiskLevel
from parakeetnest.portfolio import PortfolioHolding, PortfolioSnapshot
from parakeetnest.research import (
    ConfidenceLevel,
    InvestmentResearchService,
    RecommendationType,
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
    service = InvestmentResearchService(
        portfolio_service=portfolio,
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
    assert ticker_report.summary == "NVDA is both a portfolio holding and watchlist research item."
    assert "Datacenter demand." in ticker_report.bull_case
    assert "Export controls." in ticker_report.bear_case
    assert ticker_report.recommendation.action is RecommendationType.HOLD
    assert ticker_report.recommendation.confidence is ConfidenceLevel.HIGH
    assert ticker_report.recommendation.evidence
    assert ticker_report.recommendation.risks
    assert ticker_report.recommendation.catalysts
    assert portfolio.calls == ["main"]
    assert watchlist.calls == ["NVDA"]
    assert intelligence.calls == [("NVDA", date(2026, 7, 1))]


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
    assert ticker_report.recommendation.action is RecommendationType.WATCH
    assert ticker_report.recommendation.confidence is ConfidenceLevel.LOW
    assert ticker_report.risks[0].summary == "China demand risk."
    assert ticker_report.catalysts[0].summary == "Services growth."


def test_generate_report_uses_explicit_research_gap_when_no_context_connected() -> None:
    service = InvestmentResearchService()

    report = service.generate_report(("TSLA",), generated_at=AS_OF)

    ticker_report = report.ticker_reports[0]
    assert ticker_report.summary == (
        "TSLA is included for research, but connected context is limited."
    )
    assert ticker_report.recommendation.action is RecommendationType.WATCH
    assert ticker_report.recommendation.confidence is ConfidenceLevel.LOW
    assert ticker_report.findings[0].source == "research_service"
    assert "No portfolio service connected." in ticker_report.evidence_notes


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


def test_committee_opinions_keep_persona_specific_lenses() -> None:
    service = InvestmentResearchService()

    report = service.generate_report(("NVDA",), generated_at=AS_OF)
    opinions = {opinion.display_name: opinion for opinion in report.committee_opinions}

    assert opinions["Dongdong"].stance == "neutral"
    assert "upside" in opinions["Dongdong"].reasoning_summary
    assert "catalyst" in opinions["Dongdong"].suggested_action.lower()
    assert "fundamentals" in opinions["Xixi"].reasoning_summary
    assert "valuation" in opinions["Xixi"].suggested_action
    assert opinions["Youyou"].stance == "cautious"
    assert "capital preservation" in opinions["Youyou"].reasoning_summary
    assert "advisory only" in opinions["Youyou"].suggested_action


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
