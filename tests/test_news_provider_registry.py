"""Tests for news provider registration and configuration."""

from __future__ import annotations

import pytest

from parakeetnest.config import AppConfig, NewsConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.news import (
    MockNewsProvider,
    NewsArticle,
    NewsProviderRegistry,
    NewsQuery,
    NewsService,
    YahooFinanceNewsProvider,
    create_news_provider_registry,
)


class RecordingNewsProvider:
    """News provider test double for registry lookups."""

    def __init__(self, provider_name: str = "recording") -> None:
        self.provider_name = provider_name

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        """Return no articles; registry tests only need provider identity."""
        return []


def test_registry_registers_and_gets_provider() -> None:
    registry = NewsProviderRegistry()
    provider = RecordingNewsProvider()

    registry.register("recording", provider)

    assert registry.get("recording") is provider
    assert [
        (registration.provider_id, registration.provider)
        for registration in registry.list_registrations()
    ] == [("recording", provider)]


def test_registry_normalizes_provider_ids() -> None:
    registry = NewsProviderRegistry()
    provider = RecordingNewsProvider()

    registry.register("  Mockish  ", provider)

    assert registry.get("MOCKISH") is provider


def test_registry_rejects_duplicate_registration() -> None:
    registry = NewsProviderRegistry()
    registry.register("mock", RecordingNewsProvider("first"))

    with pytest.raises(ValueError, match="News provider already registered: mock"):
        registry.register("MOCK", RecordingNewsProvider("second"))


def test_registry_unknown_provider_lookup_raises_clear_config_error() -> None:
    registry = create_news_provider_registry()

    with pytest.raises(ConfigurationError, match="Unknown news provider: missing"):
        registry.get("missing")


def test_default_news_provider_is_mock() -> None:
    config = AppConfig()
    registry = create_news_provider_registry()

    provider = registry.default()

    assert config.news == NewsConfig(provider="mock")
    assert isinstance(provider, MockNewsProvider)


def test_selecting_configured_news_provider_works() -> None:
    config = AppConfig(news={"provider": "mock"})
    registry = create_news_provider_registry()

    provider = registry.get(config.news.provider)
    service = NewsService(provider)

    articles = service.get_news(NewsQuery(symbols=["AMD"]))

    assert isinstance(provider, MockNewsProvider)
    assert articles[0].provider == "mock"
    assert articles[0].symbols == ["AMD"]


def test_registry_lookup_for_yahoo_returns_yahoo_provider() -> None:
    registry = create_news_provider_registry()

    provider = registry.get("yahoo")

    assert isinstance(provider, YahooFinanceNewsProvider)
