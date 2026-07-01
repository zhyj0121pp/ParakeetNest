"""Tests for the investment research report service."""

from __future__ import annotations

from datetime import UTC, date, datetime

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
