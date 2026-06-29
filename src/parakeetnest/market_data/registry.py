"""Registry for configured market data providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from parakeetnest.exceptions import ConfigurationError
from parakeetnest.market_data.mock_provider import MockMarketDataProvider
from parakeetnest.market_data.provider import MarketDataProvider
from parakeetnest.market_data.yahoo import YahooFinanceMarketDataProvider


MarketDataProviderFactory = Callable[[], MarketDataProvider]


@dataclass(frozen=True)
class MarketDataProviderRegistration:
    """A provider factory registered under a stable Market Data Layer ID."""

    provider_id: str
    factory: MarketDataProviderFactory


class MarketDataProviderRegistry:
    """Register and resolve market data providers from configuration."""

    def __init__(self) -> None:
        self._registrations: dict[str, MarketDataProviderRegistration] = {}

    def register(
        self,
        provider_id: str,
        factory: MarketDataProviderFactory,
    ) -> None:
        """Register a provider factory under a unique provider ID."""
        normalized_provider_id = provider_id.strip().lower()
        if normalized_provider_id in self._registrations:
            raise ValueError(
                f"Market data provider already registered: {normalized_provider_id}"
            )

        self._registrations[normalized_provider_id] = MarketDataProviderRegistration(
            provider_id=normalized_provider_id,
            factory=factory,
        )

    def list_registrations(self) -> tuple[MarketDataProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def resolve(self, provider_id: str) -> MarketDataProvider:
        """Create the provider selected by configuration."""
        normalized_provider_id = provider_id.strip().lower()
        try:
            registration = self._registrations[normalized_provider_id]
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown market data provider: "
                f"{provider_id}. Available providers: {available_provider_ids}"
            ) from error
        return registration.factory()


def create_market_data_provider_registry() -> MarketDataProviderRegistry:
    """Create the default market data provider registry."""
    registry = MarketDataProviderRegistry()
    registry.register("mock", MockMarketDataProvider)
    registry.register("yahoo", YahooFinanceMarketDataProvider)
    return registry


__all__ = [
    "MarketDataProviderFactory",
    "MarketDataProviderRegistration",
    "MarketDataProviderRegistry",
    "create_market_data_provider_registry",
]
