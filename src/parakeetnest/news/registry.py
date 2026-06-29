"""Registry for configured news providers."""

from __future__ import annotations

from dataclasses import dataclass

from parakeetnest.exceptions import ConfigurationError
from parakeetnest.news.mock import MockNewsProvider
from parakeetnest.news.provider import NewsProvider
from parakeetnest.news.yahoo import YahooFinanceNewsProvider


@dataclass(frozen=True)
class NewsProviderRegistration:
    """A provider registered under a stable News Layer ID."""

    provider_id: str
    provider: NewsProvider


class NewsProviderRegistry:
    """Register and look up news providers from configuration."""

    def __init__(self, *, default_provider_id: str = "mock") -> None:
        self._default_provider_id = self._normalize_provider_id(default_provider_id)
        self._registrations: dict[str, NewsProviderRegistration] = {}

    def register(self, provider_id: str, provider: NewsProvider) -> None:
        """Register a provider under a unique provider ID."""
        normalized_provider_id = self._normalize_provider_id(provider_id)
        if normalized_provider_id in self._registrations:
            raise ValueError(f"News provider already registered: {normalized_provider_id}")

        self._registrations[normalized_provider_id] = NewsProviderRegistration(
            provider_id=normalized_provider_id,
            provider=provider,
        )

    def list_registrations(self) -> tuple[NewsProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def get(self, provider_id: str) -> NewsProvider:
        """Return the provider selected by configuration."""
        normalized_provider_id = self._normalize_provider_id(provider_id)
        try:
            return self._registrations[normalized_provider_id].provider
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown news provider: "
                f"{provider_id}. Available providers: {available_provider_ids}"
            ) from error

    def default(self) -> NewsProvider:
        """Return the configured default provider."""
        return self.get(self._default_provider_id)

    @staticmethod
    def _normalize_provider_id(provider_id: str) -> str:
        return provider_id.strip().lower()


def create_news_provider_registry() -> NewsProviderRegistry:
    """Create the default news provider registry."""
    registry = NewsProviderRegistry(default_provider_id="mock")
    registry.register("mock", MockNewsProvider())
    registry.register("yahoo", YahooFinanceNewsProvider())
    return registry


__all__ = [
    "NewsProviderRegistration",
    "NewsProviderRegistry",
    "create_news_provider_registry",
]
