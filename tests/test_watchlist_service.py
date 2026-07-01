"""Tests for provider-neutral watchlist intelligence service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistInsight,
    WatchlistIntelligenceService,
    WatchlistItem,
    WatchlistRepository,
    WatchlistSignal,
    WatchlistStatus,
    WatchlistThesis,
)


CREATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


def _item(
    symbol: str,
    *,
    theme: str | None = "AI infrastructure",
    reason: str | None = "Track AI infrastructure demand.",
    status: WatchlistStatus = WatchlistStatus.ACTIVE,
) -> WatchlistItem:
    return WatchlistItem(
        symbol=symbol,
        theme=theme,
        reason=reason,
        status=status,
        created_at=CREATED_AT,
    )


def test_build_insight_for_one_active_item() -> None:
    repository = InMemoryWatchlistRepository((_item("NVDA"),))
    service = WatchlistIntelligenceService(repository)

    insight = service.build_insight(" nvda ")

    assert insight == WatchlistInsight(
        symbol="NVDA",
        summary="Track AI infrastructure demand. Theme: AI infrastructure.",
        open_questions=(
            "Document watchlist thesis.",
            "Add current watchlist signals.",
        ),
        recommended_action="review thesis",
    )


def test_missing_item_raises_value_error() -> None:
    service = WatchlistIntelligenceService(InMemoryWatchlistRepository())

    with pytest.raises(ValueError, match="watchlist item does not exist for MSFT"):
        service.build_insight("msft")


def test_archived_item_behavior() -> None:
    archived = _item("MSFT", status=WatchlistStatus.ARCHIVED)
    repository = InMemoryWatchlistRepository((archived, _item("AAPL")))
    service = WatchlistIntelligenceService(repository)

    insight = service.build_insight("MSFT")

    assert insight.summary == "MSFT is archived on the watchlist."
    assert insight.recommended_action == "archived"
    assert service.build_all_insights() == (service.build_insight("AAPL"),)


def test_thesis_contributes_summary_bullish_and_bearish_factors() -> None:
    repository = InMemoryWatchlistRepository(
        (_item("AMD", theme=None, reason=None),)
    )
    thesis = WatchlistThesis(
        symbol="AMD",
        thesis="AI accelerator share gains remain plausible.",
        key_drivers=("MI-series traction", "hyperscaler demand"),
        risks=("margin pressure",),
    )
    service = WatchlistIntelligenceService(repository)

    insight = service.build_insight("AMD", theses=(thesis,))

    assert insight.summary == "AI accelerator share gains remain plausible."
    assert insight.bullish_factors == ("MI-series traction", "hyperscaler demand")
    assert insight.bearish_factors == ("margin pressure",)
    assert insight.recommended_action == "continue monitoring"


def test_signals_contribute_bullish_and_bearish_factors() -> None:
    repository = InMemoryWatchlistRepository((_item("TSLA"),))
    signals = (
        WatchlistSignal(
            symbol="TSLA",
            signal_type="delivery_momentum",
            summary="Deliveries are improving.",
            strength=0.7,
        ),
        WatchlistSignal(
            symbol="TSLA",
            signal_type="margin_pressure",
            summary="Incentives are rising.",
            strength=-0.4,
        ),
    )
    service = WatchlistIntelligenceService(repository)

    insight = service.build_insight("TSLA", signals=signals)

    assert insight.bullish_factors == (
        "delivery_momentum: Deliveries are improving.",
    )
    assert insight.bearish_factors == (
        "margin_pressure: Incentives are rising.",
    )


def test_missing_thesis_or_signals_creates_open_questions() -> None:
    repository = InMemoryWatchlistRepository((_item("META"),))
    thesis = WatchlistThesis(symbol="META", thesis="Ad efficiency can improve.")
    signal = WatchlistSignal(
        symbol="META",
        signal_type="revision",
        summary="Estimates are moving higher.",
        strength=0.2,
    )
    service = WatchlistIntelligenceService(repository)

    missing_both = service.build_insight("META")
    missing_signals = service.build_insight("META", theses=(thesis,))
    missing_thesis = service.build_insight("META", signals=(signal,))
    missing_neither = service.build_insight(
        "META",
        theses=(thesis,),
        signals=(signal,),
    )

    assert missing_both.open_questions == (
        "Document watchlist thesis.",
        "Add current watchlist signals.",
    )
    assert missing_signals.open_questions == ("Add current watchlist signals.",)
    assert missing_thesis.open_questions == ("Document watchlist thesis.",)
    assert missing_neither.open_questions == ()


def test_build_all_insights_returns_deterministic_symbol_order() -> None:
    repository = InMemoryWatchlistRepository(
        (
            _item("NVDA"),
            _item("AAPL"),
            _item("MSFT"),
        )
    )
    theses = (
        WatchlistThesis(symbol="MSFT", thesis="Azure demand can compound."),
        WatchlistThesis(symbol="AAPL", thesis="Services mix can support margins."),
    )
    signals = (
        WatchlistSignal(
            symbol="MSFT",
            signal_type="revision",
            summary="Estimates are rising.",
            strength=0.4,
        ),
        WatchlistSignal(
            symbol="AAPL",
            signal_type="demand",
            summary="Hardware demand is mixed.",
            strength=-0.2,
        ),
    )
    service = WatchlistIntelligenceService(repository)

    insights = service.build_all_insights(theses=theses, signals=signals)

    assert tuple(insight.symbol for insight in insights) == ("AAPL", "MSFT", "NVDA")


def test_service_depends_on_repository_abstraction() -> None:
    class StubWatchlistRepository(WatchlistRepository):
        def __init__(self, item: WatchlistItem) -> None:
            self.item = item

        def list_items(self) -> tuple[WatchlistItem, ...]:
            return (self.item,)

        def get_item(self, symbol: str) -> WatchlistItem | None:
            return self.item if symbol == self.item.symbol else None

        def add_item(self, item: WatchlistItem) -> WatchlistItem:
            return item

        def update_item(self, item: WatchlistItem) -> WatchlistItem:
            return item

        def archive_item(self, symbol: str) -> WatchlistItem:
            return self.item

    service = WatchlistIntelligenceService(StubWatchlistRepository(_item("CRM")))

    assert service.build_insight("crm").symbol == "CRM"
