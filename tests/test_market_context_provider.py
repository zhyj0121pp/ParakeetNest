"""Integration tests for market data flowing through the Context Layer."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.context import ContextRequest, ContextService
from parakeetnest.context.providers import MarketContextProvider
from parakeetnest.market_data import (
    AssetType,
    MarketDataRange,
    MarketDataService,
    MarketDataSnapshot,
    MockMarketDataProvider,
    PriceBar,
    Symbol,
)


class RecordingMarketDataProvider:
    """Market data provider test double that records service delegation."""

    def __init__(self) -> None:
        self.support_calls: list[Symbol] = []
        self.snapshot_calls: list[Symbol] = []

    def supports(self, symbol: Symbol) -> bool:
        self.support_calls.append(symbol)
        return True

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        self.snapshot_calls.append(symbol)
        return MarketDataSnapshot(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            price=100.0,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=95.0,
            volume=1_000_000.0,
        )

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        return []


def test_context_service_can_include_market_context_from_market_data_service() -> None:
    provider = RecordingMarketDataProvider()
    market_data_service = MarketDataService(provider)
    context_service = ContextService(
        providers=(MarketContextProvider(market_data_service),)
    )
    request = ContextRequest(question="Review AAPL.", symbols=("aapl",))

    context = context_service.build_context(request)

    assert provider.support_calls == [Symbol("AAPL")]
    assert provider.snapshot_calls == [Symbol("AAPL")]
    assert context.market is not None
    assert context.market.source == "market_data"
    assert context.market.points[0].symbol == "AAPL"
    assert context.market.points[0].price == 100.0
    assert context.market.points[0].daily_change == 5.0
    assert context.market.points[0].daily_change_percent == pytest.approx(5 / 95 * 100)
    assert context.metadata.sources == ("market_data",)
    assert context.metadata.data_quality_notes == (
        "market_data.source=market_data_service",
    )


def test_mock_market_data_provider_works_end_to_end_through_context_service() -> None:
    context_service = ContextService(
        providers=(
            MarketContextProvider(MarketDataService(MockMarketDataProvider())),
        )
    )
    request = ContextRequest(question="Review AMD and NVDA.", symbols=("AMD", "NVDA"))

    context = context_service.build_context(request)

    assert context.market is not None
    assert tuple(point.symbol for point in context.market.points) == ("AMD", "NVDA")
    assert tuple(point.price for point in context.market.points) == (175.25, 157.80)
    assert tuple(point.source for point in context.market.points) == (
        "market_data",
        "market_data",
    )
