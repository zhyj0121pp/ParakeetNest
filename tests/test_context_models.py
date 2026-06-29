"""Tests for Context Layer domain models."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from parakeetnest.context import (
    ContextMetadata,
    ContextRequest,
    FilingItem,
    FilingSnapshot,
    KnowledgeBaseSnapshot,
    MacroSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
    NewsItem,
    NewsSnapshot,
    PortfolioPosition,
    PortfolioSnapshot,
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
    news = NewsSnapshot(
        source="mock_news",
        fetched_at=fetched_at,
        items=(
            NewsItem(
                title="AMD expands AI accelerator roadmap",
                source="mock_news",
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
    knowledge_base = KnowledgeBaseSnapshot(
        thesis=("Own if AI data center share gains continue.",),
        discussions=("Prior committee wanted margin evidence.",),
    )
    metadata = ContextMetadata(
        generated_at=fetched_at,
        sources=(
            "mock_market",
            "mock_news",
            "mock_filings",
            "mock_portfolio",
            "mock_macro",
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
        portfolio=portfolio,
        macro=macro,
        knowledge_base=knowledge_base,
    )

    assert context.request.symbols == ("AMD",)
    assert context.market == market
    assert context.news == news
    assert context.filings == filings
    assert context.portfolio == portfolio
    assert context.macro == macro
    assert context.knowledge_base == knowledge_base
    assert context.metadata.sources[-1] == "knowledge_base"


def test_snapshot_collection_defaults_are_independent_tuples() -> None:
    """Collection defaults should be immutable empty tuples."""
    first = MeetingContext(request=ContextRequest("Review AAPL.", ("AAPL",)))
    second = MeetingContext(request=ContextRequest("Review TSLA.", ("TSLA",)))

    assert first.metadata.sources == ()
    assert second.metadata.sources == ()
    assert first.metadata.sources is second.metadata.sources
    assert KnowledgeBaseSnapshot().thesis == ()
    assert MarketSnapshot(source="empty").points == ()
    assert NewsSnapshot(source="empty").items == ()
    assert FilingSnapshot(source="empty").items == ()
    assert PortfolioSnapshot(source="empty").positions == ()
