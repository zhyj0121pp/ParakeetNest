"""Registry for configured macro data providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from parakeetnest.config import MacroConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.macro.fred import FREDMacroProvider
from parakeetnest.macro.mock import MockMacroDataProvider
from parakeetnest.macro.provider import MacroDataProvider


MacroDataProviderFactory = Callable[[MacroConfig], MacroDataProvider]


@dataclass(frozen=True)
class MacroDataProviderRegistration:
    """A provider factory registered under a stable Macro Layer ID."""

    provider_id: str
    factory: MacroDataProviderFactory


class MacroDataProviderRegistry:
    """Register and resolve macro data providers from configuration."""

    def __init__(self) -> None:
        self._registrations: dict[str, MacroDataProviderRegistration] = {}

    def register(
        self,
        provider_id: str,
        factory: MacroDataProviderFactory,
    ) -> None:
        """Register a provider factory under a unique provider ID."""
        normalized_provider_id = provider_id.strip().lower()
        if normalized_provider_id in self._registrations:
            raise ValueError(
                f"Macro data provider already registered: {normalized_provider_id}"
            )

        self._registrations[normalized_provider_id] = MacroDataProviderRegistration(
            provider_id=normalized_provider_id,
            factory=factory,
        )

    def list_registrations(self) -> tuple[MacroDataProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def resolve(self, config: MacroConfig | str) -> MacroDataProvider:
        """Create the provider selected by configuration."""
        resolved_config = self._resolve_config(config)
        normalized_provider_id = resolved_config.provider.strip().lower()
        try:
            registration = self._registrations[normalized_provider_id]
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown macro data provider: "
                f"{resolved_config.provider}. Available providers: {available_provider_ids}"
            ) from error
        return registration.factory(resolved_config)

    def _resolve_config(self, config: MacroConfig | str) -> MacroConfig:
        if isinstance(config, MacroConfig):
            return config
        return MacroConfig(provider=config)


def _create_mock_provider(config: MacroConfig) -> MacroDataProvider:
    return MockMacroDataProvider()


def _create_fred_provider(config: MacroConfig) -> MacroDataProvider:
    return FREDMacroProvider(
        api_key_env_var=config.fred_api_key_env_var,
        timeout_seconds=config.timeout,
    )


def create_macro_data_provider_registry() -> MacroDataProviderRegistry:
    """Create the default macro data provider registry."""
    registry = MacroDataProviderRegistry()
    registry.register("mock", _create_mock_provider)
    registry.register("fred", _create_fred_provider)
    return registry


__all__ = [
    "MacroDataProviderFactory",
    "MacroDataProviderRegistration",
    "MacroDataProviderRegistry",
    "create_macro_data_provider_registry",
]
