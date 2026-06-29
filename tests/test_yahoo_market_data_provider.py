"""Tests for the Yahoo Finance market data provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.market_data import (
    AssetType,
    MarketDataProvider,
    MarketDataRange,
    MarketDataSnapshot,
    ProviderError,
    Symbol,
    YahooFinanceMarketDataProvider,
)


class FakeTicker:
    """Minimal yfinance Ticker double used to avoid network calls."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.fast_info = {
            "currency": "USD",
            "last_price": 210.25,
            "previous_close": 208.0,
            "open": 209.5,
            "day_high": 211.0,
            "day_low": 207.9,
            "last_volume": 45_000_000,
            "regular_market_time": 1_782_738_000,
        }
        self.info = {"quoteType": "EQUITY"}
        self.history_calls: list[dict[str, object]] = []

    def history(self, **kwargs: object) -> "FakeHistory":
        self.history_calls.append(kwargs)
        return FakeHistory()


class FakeHistory:
    """Small DataFrame-like history double."""

    def iterrows(self) -> object:
        return iter(
            [
                (
                    datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                    {
                        "Open": 207.5,
                        "High": 211.0,
                        "Low": 206.75,
                        "Close": 210.25,
                        "Volume": 45_000_000,
                    },
                )
            ]
        )


class FakeYFinance:
    """Minimal yfinance module double."""

    def __init__(self) -> None:
        self.tickers: list[FakeTicker] = []

    def Ticker(self, symbol: str) -> FakeTicker:
        ticker = FakeTicker(symbol)
        self.tickers.append(ticker)
        return ticker


def test_yahoo_provider_satisfies_market_data_provider_protocol() -> None:
    """Yahoo provider should remain compatible with the provider protocol."""
    provider: MarketDataProvider = YahooFinanceMarketDataProvider(FakeYFinance())

    assert isinstance(provider, MarketDataProvider)
    assert provider.supports(Symbol("aapl")) is True


def test_get_quote_maps_yfinance_quote_to_domain_snapshot() -> None:
    """Quotes should be mapped into provider-agnostic domain models."""
    provider = YahooFinanceMarketDataProvider(FakeYFinance())

    quote = provider.get_quote("aapl")

    assert isinstance(quote, MarketDataSnapshot)
    assert quote == MarketDataSnapshot(
        symbol=Symbol("AAPL"),
        asset_type=AssetType.STOCK,
        price=210.25,
        currency="USD",
        timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
        previous_close=208.0,
        open=209.5,
        high=211.0,
        low=207.9,
        volume=45_000_000.0,
    )


def test_get_quotes_returns_domain_snapshots_for_all_symbols() -> None:
    """Batch quotes should not expose yfinance or pandas objects."""
    fake_yfinance = FakeYFinance()
    provider = YahooFinanceMarketDataProvider(fake_yfinance)

    quotes = provider.get_quotes([Symbol("aapl"), "msft"])

    assert [quote.symbol for quote in quotes] == [Symbol("AAPL"), Symbol("MSFT")]
    assert all(isinstance(quote, MarketDataSnapshot) for quote in quotes)
    assert [ticker.symbol for ticker in fake_yfinance.tickers] == ["AAPL", "MSFT"]


def test_get_snapshot_delegates_to_quote_mapping() -> None:
    """The existing provider interface should use the Yahoo quote adapter."""
    provider = YahooFinanceMarketDataProvider(FakeYFinance())

    snapshot = provider.get_snapshot(Symbol("aapl"))

    assert snapshot.symbol == Symbol("AAPL")
    assert snapshot.price == 210.25


def test_get_price_history_maps_dataframe_rows_to_price_bars() -> None:
    """History support should keep DataFrame-like objects inside the provider."""
    fake_yfinance = FakeYFinance()
    provider = YahooFinanceMarketDataProvider(fake_yfinance)
    data_range = MarketDataRange(period="5d", interval="1d")

    history = provider.get_price_history(Symbol("aapl"), data_range)

    assert len(history) == 1
    assert history[0].symbol == Symbol("AAPL")
    assert history[0].close == 210.25
    assert fake_yfinance.tickers[0].history_calls == [
        {"period": "5d", "interval": "1d"}
    ]


def test_get_quote_raises_provider_error_when_price_is_missing() -> None:
    """Malformed Yahoo data should fail as a provider-neutral error."""

    class MissingPriceTicker(FakeTicker):
        def __init__(self, symbol: str) -> None:
            super().__init__(symbol)
            self.fast_info = {}
            self.info = {"quoteType": "EQUITY"}

    class MissingPriceYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> MissingPriceTicker:
            ticker = MissingPriceTicker(symbol)
            self.tickers.append(ticker)
            return ticker

    provider = YahooFinanceMarketDataProvider(MissingPriceYFinance())

    with pytest.raises(ProviderError, match="no usable price for AAPL"):
        provider.get_quote("aapl")
