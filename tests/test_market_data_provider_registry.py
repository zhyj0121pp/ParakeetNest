"""Tests for market data provider configuration."""

from __future__ import annotations

import pytest

from parakeetnest.config import AppConfig, MarketDataConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.market_data import (
    MarketDataService,
    MockMarketDataProvider,
    Symbol,
    YahooFinanceMarketDataProvider,
    create_market_data_provider_registry,
)


def test_default_market_data_provider_is_mock() -> None:
    config = AppConfig()
    registry = create_market_data_provider_registry()

    provider = registry.resolve(config.market_data.provider)

    assert config.market_data == MarketDataConfig(provider="mock")
    assert isinstance(provider, MockMarketDataProvider)


def test_selecting_mock_market_data_provider_works() -> None:
    config = AppConfig(market_data={"provider": "mock"})
    registry = create_market_data_provider_registry()

    provider = registry.resolve(config.market_data.provider)

    assert isinstance(provider, MockMarketDataProvider)


def test_selecting_yahoo_market_data_provider_works() -> None:
    config = AppConfig(market_data=MarketDataConfig(provider="yahoo"))
    registry = create_market_data_provider_registry()

    provider = registry.resolve(config.market_data.provider)

    assert isinstance(provider, YahooFinanceMarketDataProvider)


def test_unknown_market_data_provider_raises_clear_config_error() -> None:
    registry = create_market_data_provider_registry()

    with pytest.raises(
        ConfigurationError,
        match="Unknown market data provider: missing",
    ):
        registry.resolve("missing")


def test_market_data_service_can_use_configured_provider() -> None:
    config = AppConfig(market_data={"provider": "mock"})
    registry = create_market_data_provider_registry()
    provider = registry.resolve(config.market_data.provider)
    service = MarketDataService(provider)

    snapshot = service.get_snapshot(Symbol("AMD"))

    assert snapshot.symbol == Symbol("AMD")
    assert snapshot.price == 175.25
