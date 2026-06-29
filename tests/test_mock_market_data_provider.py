"""Tests for the deterministic mock market data provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.market_data import (
    AssetType,
    MarketDataProvider,
    MarketDataRange,
    MockMarketDataProvider,
    PriceBar,
    ProviderError,
    Symbol,
)


def test_supports_embedded_symbols() -> None:
    """The mock provider should advertise only symbols with embedded data."""
    provider = MockMarketDataProvider()

    assert provider.supports(Symbol("aapl")) is True
    assert provider.supports(Symbol("MSFT")) is True
    assert provider.supports(Symbol("nvda")) is True
    assert provider.supports(Symbol("spy")) is True
    assert provider.supports(Symbol("tsla")) is False


def test_snapshot_retrieval_returns_deterministic_snapshot() -> None:
    """Snapshots should use fixed embedded values and timestamps."""
    provider = MockMarketDataProvider()

    snapshot = provider.get_snapshot(Symbol("aapl"))

    assert snapshot.symbol == Symbol("AAPL")
    assert snapshot.asset_type is AssetType.STOCK
    assert snapshot.price == 210.25
    assert snapshot.previous_close == 208.0
    assert snapshot.currency == "USD"
    assert snapshot.timestamp == datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    assert snapshot.volume == 45_000_000.0


def test_history_retrieval_returns_daily_price_bars() -> None:
    """History should return several deterministic daily bars."""
    provider = MockMarketDataProvider()

    history = provider.get_price_history(
        Symbol("SPY"),
        MarketDataRange(period="5d", interval="1d"),
    )

    assert len(history) == 4
    assert all(isinstance(bar, PriceBar) for bar in history)
    assert all(bar.symbol == Symbol("SPY") for bar in history)
    assert history[0].start_time == datetime(2026, 6, 23, 13, 30, tzinfo=UTC)
    assert history[-1].close == 622.75
    assert history[-1].volume == 78_000_000.0


def test_unsupported_symbol_raises_provider_error() -> None:
    """Unsupported symbols should fail with the provider-neutral error type."""
    provider = MockMarketDataProvider()

    with pytest.raises(ProviderError, match="Unsupported symbol: TSLA"):
        provider.get_snapshot(Symbol("tsla"))

    with pytest.raises(ProviderError, match="Unsupported symbol: TSLA"):
        provider.get_price_history(Symbol("tsla"), MarketDataRange(interval="1d"))


def test_results_are_deterministic_between_calls() -> None:
    """Repeated calls and provider instances should return identical data."""
    first_provider = MockMarketDataProvider()
    second_provider = MockMarketDataProvider()

    first_snapshot = first_provider.get_snapshot(Symbol("NVDA"))
    second_snapshot = second_provider.get_snapshot(Symbol("nvda"))
    first_history = first_provider.get_price_history(
        Symbol("NVDA"),
        MarketDataRange(period="5d", interval="1d"),
    )
    second_history = second_provider.get_price_history(
        Symbol("nvda"),
        MarketDataRange(period="1mo", interval="1d"),
    )

    assert first_snapshot == second_snapshot
    assert first_history == second_history


def test_history_returns_a_fresh_list() -> None:
    """Mutating a returned history list should not affect later calls."""
    provider = MockMarketDataProvider()

    history = provider.get_price_history(Symbol("MSFT"), MarketDataRange())
    history.clear()

    assert len(provider.get_price_history(Symbol("MSFT"), MarketDataRange())) == 4


def test_mock_provider_satisfies_market_data_provider_protocol() -> None:
    """The mock provider should be usable through the provider protocol."""
    provider: MarketDataProvider = MockMarketDataProvider()

    assert isinstance(provider, MarketDataProvider)
    assert provider.get_snapshot(Symbol("AAPL")).price == 210.25
    assert provider.get_price_history(Symbol("AAPL"), MarketDataRange())[0].open == 203.5
