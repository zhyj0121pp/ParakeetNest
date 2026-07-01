"""Tests for WatchlistContextProvider service-backed behavior."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.context import (
    ContextProvider,
    ContextProviderResult,
    ContextRequest,
    MeetingContextPromptRenderer,
)
from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistContextProvider,
    WatchlistInsight,
    WatchlistIntelligenceService,
    WatchlistItem,
    WatchlistStatus,
)


AS_OF = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


def _item(
    symbol: str,
    *,
    status: WatchlistStatus = WatchlistStatus.ACTIVE,
) -> WatchlistItem:
    return WatchlistItem(
        symbol=symbol,
        reason=f"Track {symbol} setup.",
        theme="AI infrastructure",
        status=status,
        created_at=AS_OF,
    )


def test_provider_returns_context_with_watchlist_insights() -> None:
    repository = InMemoryWatchlistRepository((_item("NVDA"),))
    provider = WatchlistContextProvider(WatchlistIntelligenceService(repository))
    request = ContextRequest(
        question="Prepare the committee watchlist.",
        symbols=("NVDA",),
        as_of=AS_OF,
    )

    result = provider.build_context(request)

    assert result.provider_name == "watchlist"
    assert result.metadata == {"source": "watchlist_intelligence_service"}
    assert result.partial_context.watchlist is not None
    assert result.partial_context.watchlist.source == "watchlist"
    assert result.partial_context.watchlist.fetched_at == AS_OF
    assert result.partial_context.watchlist.items[0].symbol == "NVDA"
    assert result.partial_context.watchlist.items[0].summary == (
        "Track NVDA setup. Theme: AI infrastructure."
    )
    assert result.partial_context.watchlist.items[0].open_questions == (
        "Document watchlist thesis.",
        "Add current watchlist signals.",
    )
    assert result.partial_context.watchlist.items[0].recommended_action == (
        "review thesis"
    )


def test_archived_items_are_excluded() -> None:
    repository = InMemoryWatchlistRepository(
        (_item("NVDA"), _item("MSFT", status=WatchlistStatus.ARCHIVED))
    )
    provider = WatchlistContextProvider(WatchlistIntelligenceService(repository))

    result = provider.build_context(
        ContextRequest(question="Prepare watchlist.", symbols=("NVDA", "MSFT"))
    )

    assert result.partial_context.watchlist is not None
    assert tuple(
        item.symbol for item in result.partial_context.watchlist.items
    ) == ("NVDA",)


def test_empty_watchlist_produces_safe_empty_context() -> None:
    provider = WatchlistContextProvider(
        WatchlistIntelligenceService(InMemoryWatchlistRepository())
    )
    request = ContextRequest(question="Prepare watchlist.", symbols=())

    result = provider.build_context(request)
    rendered = MeetingContextPromptRenderer().render(result.partial_context)

    assert result.ok is True
    assert result.partial_context.watchlist is not None
    assert result.partial_context.watchlist.items == ()
    assert "## Watchlist\n- No watchlist insights available." in rendered


def test_output_order_is_deterministic() -> None:
    class UnsortedWatchlistIntelligenceService(WatchlistIntelligenceService):
        def __init__(self) -> None:
            pass

        def build_all_insights(self) -> tuple[WatchlistInsight, ...]:
            return (
                WatchlistInsight(symbol="TSLA", summary="Track autonomy catalyst."),
                WatchlistInsight(symbol="AAPL", summary="Track services margins."),
                WatchlistInsight(symbol="MSFT", summary="Track Azure growth."),
            )

    provider = WatchlistContextProvider(UnsortedWatchlistIntelligenceService())

    result = provider.build_context(
        ContextRequest(question="Prepare watchlist.", symbols=("TSLA", "AAPL"))
    )

    assert result.partial_context.watchlist is not None
    assert tuple(
        item.symbol for item in result.partial_context.watchlist.items
    ) == ("AAPL", "MSFT", "TSLA")


def test_provider_follows_context_provider_interface() -> None:
    provider: ContextProvider = WatchlistContextProvider(
        WatchlistIntelligenceService(InMemoryWatchlistRepository())
    )
    request = ContextRequest(question="Prepare watchlist.", symbols=())

    result = provider.build_context(request)

    assert provider.provider_name == "watchlist"
    assert provider.supports(request) is True
    assert isinstance(result, ContextProviderResult)
    assert result.partial_context.market is None
    assert result.partial_context.news is None
    assert result.partial_context.watchlist is not None
