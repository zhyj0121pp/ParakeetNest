"""Registry for configured SEC filing providers."""

from __future__ import annotations

from dataclasses import dataclass

from parakeetnest.exceptions import ConfigurationError
from parakeetnest.sec.mock import MockSecFilingProvider
from parakeetnest.sec.provider import SecFilingProvider


@dataclass(frozen=True)
class SecFilingProviderRegistration:
    """A provider registered under a stable SEC Filing Layer ID."""

    provider_id: str
    provider: SecFilingProvider


class SecFilingProviderRegistry:
    """Register and look up SEC filing providers from configuration."""

    def __init__(self, *, default_provider_id: str = "mock") -> None:
        self._default_provider_id = self._normalize_provider_id(default_provider_id)
        self._registrations: dict[str, SecFilingProviderRegistration] = {}

    def register(self, provider_id: str, provider: SecFilingProvider) -> None:
        """Register a provider under a unique provider ID."""
        normalized_provider_id = self._normalize_provider_id(provider_id)
        if normalized_provider_id in self._registrations:
            raise ValueError(
                f"SEC filing provider already registered: {normalized_provider_id}"
            )

        self._registrations[normalized_provider_id] = SecFilingProviderRegistration(
            provider_id=normalized_provider_id,
            provider=provider,
        )

    def list_registrations(self) -> tuple[SecFilingProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def get(self, provider_id: str) -> SecFilingProvider:
        """Return the provider selected by configuration."""
        normalized_provider_id = self._normalize_provider_id(provider_id)
        try:
            return self._registrations[normalized_provider_id].provider
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown SEC filing provider: "
                f"{provider_id}. Available providers: {available_provider_ids}"
            ) from error

    def default(self) -> SecFilingProvider:
        """Return the configured default provider."""
        return self.get(self._default_provider_id)

    @staticmethod
    def _normalize_provider_id(provider_id: str) -> str:
        return provider_id.strip().lower()


def create_sec_filing_provider_registry() -> SecFilingProviderRegistry:
    """Create the default SEC filing provider registry."""
    registry = SecFilingProviderRegistry(default_provider_id="mock")
    registry.register("mock", MockSecFilingProvider())
    return registry


__all__ = [
    "SecFilingProviderRegistration",
    "SecFilingProviderRegistry",
    "create_sec_filing_provider_registry",
]
