"""Tests for Context Layer domain models."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from parakeetnest.context import (
    ContextMetadata,
    ContextRequest,
    EconomicRegimeContextSnapshot,
    FilingItem,
    FilingSnapshot,
    FinancialStatementItem,
    FinancialStatementSnapshot,
    KnowledgeBaseSnapshot,
    MacroSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
    NewsContext,
    NewsItem,
    NewsSnapshot,
    PortfolioPosition,
    PortfolioSnapshot,
    SectorRotationContextSnapshot,
    ValuationContextItem,
    ValuationContextSnapshot,
)


def test_context_request_is_typed_and_immutable() -> None:
    """A context request should preserve symbols and default source choices."""
    request = ContextRequest(question="Should we buy NVDA?", symbols=("NVDA",))

    assert request.symbols == ("NVDA",)
    assert request.include_portfolio is True
    assert request.include_macro is True
    assert request.include_knowledge_base is True

    with pytest.raises(FrozenInstanceError):
        request.question = "mutated"


def test_meeting_context_composes_all_context_snapshots() -> None:
    """Meeting context should aggregate domain snapshots without side effects."""
    fetched_at = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    request = ContextRequest(
        question="Review AMD.",
        symbols=("AMD",),
        as_of=fetched_at,
    )
    market = MarketSnapshot(
        source="mock_market",
        fetched_at=fetched_at,
        points=(
            MarketDataPoint(
                symbol="AMD",
                source="mock_market",
                observed_at=fetched_at,
                price=175.25,
                daily_change_percent=1.2,
            ),
        ),
    )
    news = NewsContext(
        source="news",
        fetched_at=fetched_at,
        items=(
            NewsItem(
                title="AMD expands AI accelerator roadmap",
                source="Parakeet Wire",
                symbol="AMD",
                published_at=fetched_at,
            ),
        ),
    )
    filings = FilingSnapshot(
        source="mock_filings",
        fetched_at=fetched_at,
        items=(
            FilingItem(
                symbol="AMD",
                filing_type="10-Q",
                source="mock_filings",
                filed_at=fetched_at,
            ),
        ),
    )
    financials = FinancialStatementSnapshot(
        source="mock_financials",
        fetched_at=fetched_at,
        items=(
            FinancialStatementItem(
                symbol="AMD",
                period_type="annual",
                source="mock",
                revenue=100.0,
                gross_profit=60.0,
                operating_income=30.0,
                net_income=20.0,
                eps=2.5,
                cash=10.0,
                total_debt=5.0,
                total_equity=50.0,
                operating_cash_flow=25.0,
                free_cash_flow=18.0,
                fiscal_year=2026,
                currency="USD",
            ),
        ),
    )
    valuation = ValuationContextSnapshot(
        source="valuation",
        fetched_at=fetched_at,
        items=(
            ValuationContextItem(
                symbol="AMD",
                as_of_date=date(2026, 6, 29),
                fiscal_period="TTM",
                metrics={"pe_ratio": 35.0},
                calculation_notes=("Calculated from normalized inputs.",),
                confidence="medium",
                data_sources=("market snapshot", "financial statements"),
            ),
        ),
    )
    portfolio = PortfolioSnapshot(
        source="mock_portfolio",
        fetched_at=fetched_at,
        positions=(
            PortfolioPosition(
                symbol="AMD",
                quantity=10,
                market_value=1752.50,
                weight=0.08,
            ),
        ),
        cash_balance=500.0,
        total_value=2252.50,
    )
    macro = MacroSnapshot(
        source="mock_macro",
        fetched_at=fetched_at,
        indicators=("Fed policy remains restrictive.",),
        observed_on=date(2026, 6, 29),
    )
    economic_regime = EconomicRegimeContextSnapshot(
        source="economic_regime",
        fetched_at=fetched_at,
        regime="expansion",
        confidence="medium",
        observed_on=date(2026, 6, 29),
        indicators=("GDP Growth (growth): 2.1 percent as of 2026-06-29",),
        summary="Growth is steady.",
        regime_source="economic_regime_service",
    )
    sector_rotation = SectorRotationContextSnapshot(
        source="sector_rotation_calculator",
        fetched_at=fetched_at,
        as_of_date=date(2026, 6, 29),
        summary="Technology leads while defensives weaken.",
        leaders=("Technology",),
        improving=("Industrials",),
        weakening=("Utilities",),
        laggards=("Real Estate",),
        unknown=("Materials",),
        evidence=("Technology: Relative return classified as leading.",),
    )
    knowledge_base = KnowledgeBaseSnapshot(
        thesis=("Own if AI data center share gains continue.",),
        discussions=("Prior committee wanted margin evidence.",),
    )
    metadata = ContextMetadata(
        generated_at=fetched_at,
        sources=(
            "mock_market",
            "news",
            "mock_filings",
            "mock_financials",
            "valuation",
            "mock_portfolio",
            "mock_macro",
            "economic_regime",
            "sector_rotation",
            "knowledge_base",
        ),
        data_quality_notes=("All context is deterministic test data.",),
    )

    context = MeetingContext(
        request=request,
        metadata=metadata,
        market=market,
        news=news,
        filings=filings,
        financials=financials,
        valuation=valuation,
        portfolio=portfolio,
        macro=macro,
        economic_regime=economic_regime,
        sector_rotation=sector_rotation,
        knowledge_base=knowledge_base,
    )

    assert context.request.symbols == ("AMD",)
    assert context.market == market
    assert context.news == news
    assert context.filings == filings
    assert context.financials == financials
    assert context.valuation == valuation
    assert context.portfolio == portfolio
    assert context.macro == macro
    assert context.economic_regime == economic_regime
    assert context.sector_rotation == sector_rotation
    assert context.knowledge_base == knowledge_base
    assert context.metadata.sources[-1] == "knowledge_base"


def test_news_context_creation() -> None:
    """NewsContext should preserve provider-neutral news items."""
    published_at = datetime(2026, 6, 29, 12, 30, tzinfo=UTC)
    news_context = NewsContext(
        source="news",
        fetched_at=published_at,
        items=(
            NewsItem(
                title="AMD expands AI accelerator roadmap",
                source="Parakeet Wire",
                symbol="AMD",
                url="https://example.com/news/amd-ai-roadmap",
                summary="AMD outlined new accelerator milestones.",
                published_at=published_at,
            ),
        ),
    )

    assert news_context.source == "news"
    assert news_context.items[0].symbol == "AMD"
    assert news_context.items[0].source == "Parakeet Wire"


def test_snapshot_collection_defaults_are_independent_tuples() -> None:
    """Collection defaults should be immutable empty tuples."""
    first = MeetingContext(request=ContextRequest("Review AAPL.", ("AAPL",)))
    second = MeetingContext(request=ContextRequest("Review TSLA.", ("TSLA",)))

    assert first.metadata.sources == ()
    assert second.metadata.sources == ()
    assert first.metadata.sources is second.metadata.sources
    assert KnowledgeBaseSnapshot().thesis == ()
    assert MarketSnapshot(source="empty").points == ()
    assert NewsContext(source="empty").items == ()
    assert NewsSnapshot(source="empty").items == ()
    assert FilingSnapshot(source="empty").items == ()
    assert FinancialStatementSnapshot(source="empty").items == ()
    assert ValuationContextSnapshot(source="empty").items == ()
    assert PortfolioSnapshot(source="empty").positions == ()
    assert SectorRotationContextSnapshot(
        source="empty",
        as_of_date=date(2026, 6, 29),
    ).leaders == ()
