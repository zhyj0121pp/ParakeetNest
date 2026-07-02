"""Tests for the Market Data Provider abstraction."""

from __future__ import annotations

import inspect
import sys
from datetime import UTC, datetime

import pytest

from parakeetnest.market_data import (
    AssetType,
    CompanyInfo,
    MarketDataProvider,
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    ProviderCapability,
    ProviderError,
    Symbol,
)


class FakeMarketDataProvider:
    """In-memory provider used to verify the provider protocol contract."""

    def supports(self, symbol: Symbol) -> bool:
        """Return whether the fake provider has static data for the symbol."""
        return symbol == Symbol("AAPL")

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Return a deterministic snapshot without external dependencies."""
        if not self.supports(symbol):
            raise ProviderError(f"Unsupported symbol: {symbol.ticker}")
        return MarketDataSnapshot(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            price=210.25,
            currency="USD",
            timestamp=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            previous_close=208.0,
        )

    def get_company_info(self, symbol: Symbol) -> CompanyInfo:
        """Return deterministic company info without external dependencies."""
        if not self.supports(symbol):
            raise ProviderError(f"Unsupported symbol: {symbol.ticker}")
        return CompanyInfo(
            symbol=symbol,
            name="Apple Inc.",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
        )

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        """Return deterministic historical bars without external dependencies."""
        if not self.supports(symbol):
            raise ProviderError(f"Unsupported symbol: {symbol.ticker}")
        assert range.interval == "1d"
        return [
            PriceBar(
                symbol=symbol,
                start_time=datetime(2026, 6, 26, 13, 30, tzinfo=UTC),
                open=207.5,
                high=211.0,
                low=206.75,
                close=210.25,
                volume=45_000_000.0,
            )
        ]


def test_mock_implementation_satisfies_market_data_provider_protocol() -> None:
    """A structurally compatible implementation should satisfy the protocol."""
    provider = FakeMarketDataProvider()

    assert isinstance(provider, MarketDataProvider)
    assert provider.supports(Symbol("aapl")) is True
    assert provider.supports(Symbol("msft")) is False


def test_provider_methods_return_provider_agnostic_market_data_models() -> None:
    """Provider APIs should use only Market Data Layer value objects."""
    provider: MarketDataProvider = FakeMarketDataProvider()
    symbol = Symbol("aapl")
    data_range = MarketDataRange(period="5d", interval="1d")

    snapshot = provider.get_snapshot(symbol)
    history = provider.get_price_history(symbol, data_range)

    assert snapshot.symbol == symbol
    assert snapshot.price == 210.25
    assert len(history) == 1
    assert history[0].symbol == symbol
    assert history[0].close == 210.25


def test_provider_method_signatures_are_intentionally_small() -> None:
    """The provider protocol should expose a small stable contract."""
    supports = inspect.signature(MarketDataProvider.supports)
    snapshot = inspect.signature(MarketDataProvider.get_snapshot)
    history = inspect.signature(MarketDataProvider.get_price_history)

    assert list(supports.parameters) == ["self", "symbol"]
    assert supports.return_annotation == "bool"
    assert list(snapshot.parameters) == ["self", "symbol"]
    assert snapshot.return_annotation == "MarketDataSnapshot"
    assert list(history.parameters) == ["self", "symbol", "range"]
    assert history.return_annotation == "list[PriceBar]"


def test_provider_capabilities_and_errors_are_provider_neutral() -> None:
    """Provider support types should not name a concrete data source."""
    assert ProviderCapability.SNAPSHOT.value == "snapshot"
    assert ProviderCapability.PRICE_HISTORY.value == "price_history"

    with pytest.raises(ProviderError, match="Unsupported symbol"):
        FakeMarketDataProvider().get_snapshot(Symbol("missing"))


def test_provider_abstraction_does_not_require_external_data_clients() -> None:
    """Importing and using the abstraction should not import network clients."""
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp"}

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = FakeMarketDataProvider()

    assert isinstance(provider.get_snapshot(Symbol("aapl")), MarketDataSnapshot)
    assert forbidden_modules.isdisjoint(sys.modules)
