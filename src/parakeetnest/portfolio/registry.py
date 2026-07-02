"""Registry for configured portfolio providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os

from parakeetnest.config import PortfolioConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.portfolio.mock_provider import MockPortfolioProvider
from parakeetnest.portfolio.provider import PortfolioProvider
from parakeetnest.portfolio.robinhood import RobinhoodPortfolioProvider


PortfolioProviderFactory = Callable[[PortfolioConfig], PortfolioProvider]


@dataclass(frozen=True)
class PortfolioProviderRegistration:
    """A provider factory registered under a stable Portfolio Layer ID."""

    provider_id: str
    factory: PortfolioProviderFactory


class PortfolioProviderRegistry:
    """Register and resolve portfolio providers from configuration."""

    def __init__(self) -> None:
        self._registrations: dict[str, PortfolioProviderRegistration] = {}

    def register(
        self,
        provider_id: str,
        factory: PortfolioProviderFactory,
    ) -> None:
        """Register a provider factory under a unique provider ID."""
        normalized_provider_id = provider_id.strip().lower()
        if normalized_provider_id in self._registrations:
            raise ValueError(
                f"Portfolio provider already registered: {normalized_provider_id}"
            )
        self._registrations[normalized_provider_id] = PortfolioProviderRegistration(
            provider_id=normalized_provider_id,
            factory=factory,
        )

    def list_registrations(self) -> tuple[PortfolioProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def resolve(self, config: PortfolioConfig | str) -> PortfolioProvider:
        """Create the provider selected by configuration."""
        resolved_config = self._resolve_config(config)
        normalized_provider_id = resolved_config.provider.strip().lower()
        try:
            registration = self._registrations[normalized_provider_id]
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown portfolio provider: "
                f"{resolved_config.provider}. Available providers: {available_provider_ids}"
            ) from error
        return registration.factory(resolved_config)

    def _resolve_config(self, config: PortfolioConfig | str) -> PortfolioConfig:
        if isinstance(config, PortfolioConfig):
            return config
        return PortfolioConfig(provider=config)


def _create_mock_provider(config: PortfolioConfig) -> PortfolioProvider:
    return MockPortfolioProvider()


def _create_robinhood_provider(config: PortfolioConfig) -> PortfolioProvider:
    return RobinhoodPortfolioProvider(
        username=_read_env(config.robinhood_username_env_var),
        password=_read_env(config.robinhood_password_env_var),
        session_token=_read_env(config.robinhood_session_token_env_var),
    )


def _read_env(env_var_name: str) -> str | None:
    value = os.getenv(env_var_name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def create_portfolio_provider_registry() -> PortfolioProviderRegistry:
    """Create the default portfolio provider registry."""
    registry = PortfolioProviderRegistry()
    registry.register("mock", _create_mock_provider)
    registry.register("robinhood", _create_robinhood_provider)
    return registry


__all__ = [
    "PortfolioProviderFactory",
    "PortfolioProviderRegistration",
    "PortfolioProviderRegistry",
    "create_portfolio_provider_registry",
]
