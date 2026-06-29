"""Tests for the provider-agnostic market data service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.market_data import (
    AssetType,
    MarketDataProvider,
    MarketDataRange,
    MarketDataService,
    MarketDataSnapshot,
    MockMarketDataProvider,
    PriceBar,
    ProviderError,
    Symbol,
)


class SpyMarketDataProvider:
    """Provider test double that records service delegation."""

    def __init__(self, supported: bool = True) -> None:
        self.supported = supported
        self.support_calls: list[Symbol] = []
        self.snapshot_calls: list[Symbol] = []
        self.history_calls: list[tuple[Symbol, MarketDataRange]] = []
        self.snapshot = MarketDataSnapshot(
            symbol=Symbol("AAPL"),
            asset_type=AssetType.STOCK,
            price=210.25,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
        )
        self.history = [
            PriceBar(
                symbol=Symbol("AAPL"),
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=207.5,
                high=211.0,
                low=206.75,
                close=210.25,
                volume=45_000_000.0,
            )
        ]

    def supports(self, symbol: Symbol) -> bool:
        """Record and return support for the requested symbol."""
        self.support_calls.append(symbol)
        return self.supported

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Record snapshot delegation."""
        self.snapshot_calls.append(symbol)
        return self.snapshot

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        """Record history delegation."""
        self.history_calls.append((symbol, range))
        return self.history


def test_snapshot_delegates_to_provider_after_support_check() -> None:
    """The service should validate support before delegating snapshots."""
    provider = SpyMarketDataProvider()
    service = MarketDataService(provider)
    symbol = Symbol("aapl")

    snapshot = service.get_snapshot(symbol)

    assert snapshot is provider.snapshot
    assert provider.support_calls == [symbol]
    assert provider.snapshot_calls == [symbol]


def test_history_delegates_to_provider_after_support_check() -> None:
    """The service should validate support before delegating history."""
    provider = SpyMarketDataProvider()
    service = MarketDataService(provider)
    symbol = Symbol("AAPL")
    data_range = MarketDataRange(period="5d", interval="1d")

    history = service.get_price_history(symbol, data_range)

    assert history is provider.history
    assert provider.support_calls == [symbol]
    assert provider.history_calls == [(symbol, data_range)]


def test_unsupported_symbols_raise_provider_error_without_fetching() -> None:
    """Unsupported symbols should fail before provider data methods are called."""
    provider = SpyMarketDataProvider(supported=False)
    service = MarketDataService(provider)
    symbol = Symbol("tsla")
    data_range = MarketDataRange(period="5d", interval="1d")

    with pytest.raises(ProviderError, match="Unsupported symbol: TSLA"):
        service.get_snapshot(symbol)

    with pytest.raises(ProviderError, match="Unsupported symbol: TSLA"):
        service.get_price_history(symbol, data_range)

    assert provider.support_calls == [symbol, symbol]
    assert provider.snapshot_calls == []
    assert provider.history_calls == []


def test_service_works_with_mock_market_data_provider() -> None:
    """The concrete mock provider should be usable through the service."""
    provider: MarketDataProvider = MockMarketDataProvider()
    service = MarketDataService(provider)

    snapshot = service.get_snapshot(Symbol("aapl"))
    history = service.get_price_history(
        Symbol("aapl"),
        MarketDataRange(period="5d", interval="1d"),
    )

    assert snapshot.symbol == Symbol("AAPL")
    assert snapshot.price == 210.25
    assert len(history) == 4
    assert history[-1].close == 210.25
