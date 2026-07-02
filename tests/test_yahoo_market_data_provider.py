"""Tests for the Yahoo Finance market data provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.market_data import (
    AssetType,
    CompanyInfo,
    InvalidSymbolError,
    MalformedMarketDataError,
    MarketDataProvider,
    MarketDataRange,
    MarketDataSnapshot,
    ProviderUnavailableError,
    Symbol,
    YahooFinanceMarketDataProvider,
)


FAKE_YAHOO_COMPANY_INFO = {
    "longName": "Apple Inc.",
    "quoteType": "EQUITY",
    "exchange": "NMS",
    "currency": "USD",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "country": "United States",
    "website": "https://www.apple.com",
    "marketCap": 3_200_000_000_000,
    "fullTimeEmployees": 164_000,
    "longBusinessSummary": "Apple designs, manufactures, and markets consumer technology.",
}


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
        self.info = FAKE_YAHOO_COMPANY_INFO.copy()
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


def test_get_company_info_maps_yfinance_info_to_domain_model() -> None:
    """Company info should be mapped into provider-agnostic domain models."""
    provider = YahooFinanceMarketDataProvider(FakeYFinance())

    company_info = provider.get_company_info("aapl")

    assert company_info == CompanyInfo(
        symbol=Symbol("AAPL"),
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NMS",
        currency="USD",
        sector="Technology",
        industry="Consumer Electronics",
        country="United States",
        website="https://www.apple.com",
        market_cap=3_200_000_000_000.0,
        full_time_employees=164_000,
        summary="Apple designs, manufactures, and markets consumer technology.",
    )


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


def test_get_company_info_raises_malformed_error_for_empty_response() -> None:
    """Empty company info responses should fail as provider-neutral errors."""

    class EmptyCompanyInfoTicker(FakeTicker):
        def __init__(self, symbol: str) -> None:
            super().__init__(symbol)
            self.info = {}

    class EmptyCompanyInfoYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> EmptyCompanyInfoTicker:
            ticker = EmptyCompanyInfoTicker(symbol)
            self.tickers.append(ticker)
            return ticker

    provider = YahooFinanceMarketDataProvider(EmptyCompanyInfoYFinance())

    with pytest.raises(MalformedMarketDataError, match="empty company info response"):
        provider.get_company_info("aapl")


def test_get_company_info_raises_malformed_error_for_missing_usable_name() -> None:
    """Company info responses need a usable provider-neutral company name."""

    class MissingNameTicker(FakeTicker):
        def __init__(self, symbol: str) -> None:
            super().__init__(symbol)
            self.info = {
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "currency": "USD",
            }

    class MissingNameYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> MissingNameTicker:
            ticker = MissingNameTicker(symbol)
            self.tickers.append(ticker)
            return ticker

    provider = YahooFinanceMarketDataProvider(MissingNameYFinance())

    with pytest.raises(MalformedMarketDataError, match="no usable company name"):
        provider.get_company_info("aapl")


def test_get_quote_raises_malformed_error_when_price_is_missing() -> None:
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

    with pytest.raises(MalformedMarketDataError, match="no usable price for AAPL"):
        provider.get_quote("aapl")


def test_get_quote_raises_invalid_symbol_for_empty_symbol() -> None:
    """Invalid symbols should fail without calling yfinance."""
    fake_yfinance = FakeYFinance()
    provider = YahooFinanceMarketDataProvider(fake_yfinance)

    with pytest.raises(InvalidSymbolError, match="Symbol must not be empty"):
        provider.get_quote(" ")

    assert fake_yfinance.tickers == []


def test_get_quote_raises_malformed_error_for_empty_response() -> None:
    """Empty provider responses are not retried."""

    class EmptyTicker(FakeTicker):
        def __init__(self, symbol: str) -> None:
            super().__init__(symbol)
            self.fast_info = {}
            self.info = {}

    class EmptyYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> EmptyTicker:
            ticker = EmptyTicker(symbol)
            self.tickers.append(ticker)
            return ticker

    fake_yfinance = EmptyYFinance()
    provider = YahooFinanceMarketDataProvider(fake_yfinance, retry_delay_seconds=0)

    with pytest.raises(MalformedMarketDataError, match="empty response"):
        provider.get_quote("aapl")

    assert len(fake_yfinance.tickers) == 1


def test_get_quote_raises_malformed_error_for_bad_quote_shape() -> None:
    """Malformed quote payloads should not leak provider or pandas errors."""

    class BadMapping:
        def items(self) -> object:
            raise ValueError("bad dataframe shape")

    class BadQuoteTicker(FakeTicker):
        def __init__(self, symbol: str) -> None:
            super().__init__(symbol)
            self.fast_info = BadMapping()

    class BadQuoteYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> BadQuoteTicker:
            ticker = BadQuoteTicker(symbol)
            self.tickers.append(ticker)
            return ticker

    provider = YahooFinanceMarketDataProvider(BadQuoteYFinance(), retry_delay_seconds=0)

    with pytest.raises(MalformedMarketDataError, match="non-mapping|malformed"):
        provider.get_quote("aapl")


def test_timeout_maps_to_provider_unavailable() -> None:
    """Timeout exceptions should be converted to domain errors."""

    class TimeoutYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> FakeTicker:
            raise TimeoutError("read timed out")

    provider = YahooFinanceMarketDataProvider(
        TimeoutYFinance(),
        max_attempts=1,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError, match="temporarily unavailable"):
        provider.get_quote("aapl")


def test_network_failure_maps_to_provider_unavailable() -> None:
    """Network exceptions should be converted to domain errors."""

    class NetworkYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> FakeTicker:
            raise ConnectionError("connection reset")

    provider = YahooFinanceMarketDataProvider(
        NetworkYFinance(),
        max_attempts=1,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError, match="temporarily unavailable"):
        provider.get_quote("aapl")


def test_retry_succeeds_after_transient_failure() -> None:
    """Transient provider failures should be retried inside the Yahoo provider."""

    class FlakyYFinance(FakeYFinance):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def Ticker(self, symbol: str) -> FakeTicker:
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("read timed out")
            return super().Ticker(symbol)

    fake_yfinance = FlakyYFinance()
    provider = YahooFinanceMarketDataProvider(
        fake_yfinance,
        max_attempts=2,
        retry_delay_seconds=0,
    )

    snapshot = provider.get_quote("aapl")

    assert snapshot.price == 210.25
    assert fake_yfinance.calls == 2


def test_retry_exhausted_raises_provider_unavailable() -> None:
    """Retry exhaustion should return the domain error, not the root exception."""

    class AlwaysTimeoutYFinance(FakeYFinance):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def Ticker(self, symbol: str) -> FakeTicker:
            self.calls += 1
            raise TimeoutError("read timed out")

    fake_yfinance = AlwaysTimeoutYFinance()
    provider = YahooFinanceMarketDataProvider(
        fake_yfinance,
        max_attempts=3,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError):
        provider.get_quote("aapl")

    assert fake_yfinance.calls == 3


def test_yfinance_exception_does_not_escape() -> None:
    """Provider-specific exceptions should not cross the provider boundary."""

    class YFinanceBoom(Exception):
        pass

    class BrokenYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> FakeTicker:
            raise YFinanceBoom("provider exploded")

    provider = YahooFinanceMarketDataProvider(
        BrokenYFinance(),
        max_attempts=1,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider.get_quote("aapl")

    assert not isinstance(exc_info.value, YFinanceBoom)
