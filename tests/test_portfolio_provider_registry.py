"""Tests for portfolio provider configuration."""

from __future__ import annotations

import pytest

from parakeetnest.config import AppConfig, PortfolioConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.portfolio import (
    MockPortfolioProvider,
    PortfolioService,
    create_portfolio_provider_registry,
)
from parakeetnest.portfolio.robinhood import RobinhoodPortfolioProvider


def test_default_portfolio_provider_is_mock() -> None:
    config = AppConfig()
    registry = create_portfolio_provider_registry()

    provider = registry.resolve(config.portfolio)

    assert config.portfolio == PortfolioConfig(provider="mock")
    assert isinstance(provider, MockPortfolioProvider)


def test_selecting_mock_portfolio_provider_works() -> None:
    config = AppConfig(portfolio={"provider": "mock"})
    registry = create_portfolio_provider_registry()

    provider = registry.resolve(config.portfolio)

    assert isinstance(provider, MockPortfolioProvider)


def test_selecting_robinhood_portfolio_provider_uses_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_RH_USER", "xixi")
    monkeypatch.setenv("TEST_RH_PASS", "secret")
    config = AppConfig(
        portfolio={
            "provider": "robinhood",
            "robinhood_username_env_var": "TEST_RH_USER",
            "robinhood_password_env_var": "TEST_RH_PASS",
        }
    )
    registry = create_portfolio_provider_registry()

    provider = registry.resolve(config.portfolio)

    assert isinstance(provider, RobinhoodPortfolioProvider)
    assert provider._username == "xixi"
    assert provider._password == "secret"


def test_selecting_robinhood_portfolio_provider_uses_session_cache_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    cache_path = tmp_path / "robinhood.pickle"
    monkeypatch.setenv("ROBINHOOD_SESSION_CACHE_PATH", str(cache_path))
    config = AppConfig(portfolio={"provider": "robinhood"})
    registry = create_portfolio_provider_registry()

    provider = registry.resolve(config.portfolio)

    assert isinstance(provider, RobinhoodPortfolioProvider)
    assert provider._session_cache_path == cache_path


def test_selecting_robinhood_portfolio_provider_prefers_configured_cache_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    env_cache_path = tmp_path / "env-robinhood.pickle"
    config_cache_path = tmp_path / "config-robinhood.pickle"
    monkeypatch.setenv("ROBINHOOD_SESSION_CACHE_PATH", str(env_cache_path))
    config = AppConfig(
        portfolio={
            "provider": "robinhood",
            "robinhood_session_cache_path": str(config_cache_path),
        }
    )
    registry = create_portfolio_provider_registry()

    provider = registry.resolve(config.portfolio)

    assert isinstance(provider, RobinhoodPortfolioProvider)
    assert provider._session_cache_path == config_cache_path


def test_unknown_portfolio_provider_raises_clear_config_error() -> None:
    registry = create_portfolio_provider_registry()

    with pytest.raises(
        ConfigurationError,
        match="Unknown portfolio provider: missing",
    ):
        registry.resolve("missing")


def test_portfolio_service_can_use_configured_default_provider() -> None:
    config = AppConfig(portfolio={"provider": "mock"})
    registry = create_portfolio_provider_registry()
    provider = registry.resolve(config.portfolio)
    service = PortfolioService(provider)

    snapshot = service.get_snapshot("mock-main")

    assert snapshot.account_id == "mock-main"
    assert snapshot.symbols() == ("NVDA", "MSFT", "AAPL", "MU", "CRDO", "RKLB", "OKLO")
