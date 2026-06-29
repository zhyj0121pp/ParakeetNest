"""Tests for Market Data Layer domain models."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from parakeetnest.market_data import (
    AssetType,
    MarketDataError,
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    Symbol,
)


def test_symbol_normalizes_components_and_is_immutable() -> None:
    """Symbols should normalize casing and whitespace for stable identity."""
    symbol = Symbol(" nvda ", exchange=" nasdaq ", market=" us ")

    assert symbol.ticker == "NVDA"
    assert symbol.exchange == "NASDAQ"
    assert symbol.market == "US"

    with pytest.raises(FrozenInstanceError):
        symbol.ticker = "AMD"


def test_asset_type_enum_values_are_provider_agnostic() -> None:
    """Asset types should expose stable string values."""
    assert AssetType.STOCK.value == "stock"
    assert AssetType.ETF.value == "etf"
    assert AssetType.INDEX.value == "index"
    assert AssetType.CRYPTO.value == "crypto"
    assert AssetType.UNKNOWN.value == "unknown"


def test_market_data_snapshot_creation() -> None:
    """A snapshot should capture point-in-time market data for one symbol."""
    timestamp = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    snapshot = MarketDataSnapshot(
        symbol=Symbol("aapl"),
        asset_type=AssetType.STOCK,
        price=210.25,
        currency="USD",
        timestamp=timestamp,
        previous_close=208.0,
        open=209.5,
        high=211.0,
        low=207.9,
        volume=45_000_000.0,
    )

    assert snapshot.symbol == Symbol("AAPL")
    assert snapshot.asset_type is AssetType.STOCK
    assert snapshot.price == 210.25
    assert snapshot.currency == "USD"
    assert snapshot.timestamp == timestamp
    assert snapshot.previous_close == 208.0
    assert snapshot.open == 209.5
    assert snapshot.high == 211.0
    assert snapshot.low == 207.9
    assert snapshot.volume == 45_000_000.0


def test_price_bar_creation_and_immutability() -> None:
    """A price bar should capture OHLCV data for one interval."""
    start_time = datetime(2026, 6, 29, 14, 30, tzinfo=UTC)
    bar = PriceBar(
        symbol=Symbol("spy"),
        start_time=start_time,
        open=620.0,
        high=623.5,
        low=619.25,
        close=622.75,
        volume=10_500_000.0,
    )

    assert bar.symbol == Symbol("SPY")
    assert bar.start_time == start_time
    assert bar.open == 620.0
    assert bar.high == 623.5
    assert bar.low == 619.25
    assert bar.close == 622.75
    assert bar.volume == 10_500_000.0

    with pytest.raises(FrozenInstanceError):
        bar.close = 621.0


def test_market_data_range_creation() -> None:
    """A range should carry provider-neutral period or start/end requests."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 6, 29, tzinfo=UTC)
    historical_range = MarketDataRange(
        period="6mo",
        interval="1d",
        start=start,
        end=end,
    )

    assert historical_range.period == "6mo"
    assert historical_range.interval == "1d"
    assert historical_range.start == start
    assert historical_range.end == end


def test_market_data_error_creation_and_immutability() -> None:
    """A market data error should describe failures without provider clients."""
    error = MarketDataError(
        code="symbol_not_found",
        message="Symbol was not found.",
        symbol=Symbol("missing"),
        retryable=False,
        details="No matching instrument exists.",
    )

    assert error.code == "symbol_not_found"
    assert error.message == "Symbol was not found."
    assert error.symbol == Symbol("MISSING")
    assert error.retryable is False
    assert error.details == "No matching instrument exists."

    with pytest.raises(FrozenInstanceError):
        error.message = "mutated"
