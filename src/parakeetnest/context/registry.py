"""Simple registry for Context Layer providers."""

from __future__ import annotations

from dataclasses import dataclass, replace

from parakeetnest.context.provider import ContextProvider


@dataclass(frozen=True)
class ContextProviderRegistration:
    """A provider registered under a stable Context Layer ID."""

    provider_id: str
    provider: ContextProvider
    enabled: bool = True


class ContextProviderRegistry:
    """Register and resolve context providers without framework-style DI."""

    def __init__(self) -> None:
        self._registrations: dict[str, ContextProviderRegistration] = {}

    def register(
        self,
        provider_id: str,
        provider: ContextProvider,
        *,
        enabled: bool = True,
    ) -> None:
        """Register a provider under a unique provider ID."""
        if provider_id in self._registrations:
            raise ValueError(f"Context provider already registered: {provider_id}")

        self._registrations[provider_id] = ContextProviderRegistration(
            provider_id=provider_id,
            provider=provider,
            enabled=enabled,
        )

    def list_registrations(self) -> tuple[ContextProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def list_providers(self) -> tuple[ContextProvider, ...]:
        """Return all registered provider instances in registration order."""
        return tuple(
            registration.provider for registration in self._registrations.values()
        )

    def resolve_enabled_providers(self) -> tuple[ContextProvider, ...]:
        """Return enabled provider instances in registration order."""
        return tuple(
            registration.provider
            for registration in self._registrations.values()
            if registration.enabled
        )

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        """Enable or disable a registered provider."""
        registration = self._registration_for(provider_id)
        self._registrations[provider_id] = replace(registration, enabled=enabled)

    def enable(self, provider_id: str) -> None:
        """Enable a registered provider."""
        self.set_enabled(provider_id, True)

    def disable(self, provider_id: str) -> None:
        """Disable a registered provider."""
        self.set_enabled(provider_id, False)

    def _registration_for(self, provider_id: str) -> ContextProviderRegistration:
        try:
            return self._registrations[provider_id]
        except KeyError as error:
            raise KeyError(f"Unknown context provider: {provider_id}") from error
