"""Registry for configured financial statement providers."""

from __future__ import annotations

from parakeetnest.financials.provider import FinancialStatementProvider


class FinancialStatementProviderRegistry:
    """Register and look up financial statement providers."""

    def __init__(
        self,
        providers: list[FinancialStatementProvider] | None = None,
        default_provider: str | None = None,
    ) -> None:
        self._providers: dict[str, FinancialStatementProvider] = {}
        self._default_provider_name: str | None = None

        for provider in providers or []:
            self.register_provider(provider)

        if default_provider is not None:
            self.set_default_provider(default_provider)
        elif len(self._providers) == 1:
            self._default_provider_name = next(iter(self._providers))

    def register_provider(self, provider: FinancialStatementProvider) -> None:
        """Register a provider under its unique provider name."""
        provider_name = self._normalize_provider_name(provider.name)
        if provider_name in self._providers:
            raise ValueError(
                f"Financial statement provider already registered: {provider_name}"
            )

        self._providers[provider_name] = provider

    def unregister_provider(self, name: str) -> None:
        """Remove a provider by name."""
        provider_name = self._normalize_provider_name(name)
        try:
            del self._providers[provider_name]
        except KeyError as error:
            raise KeyError(f"Unknown financial statement provider: {name}") from error

        if self._default_provider_name == provider_name:
            self._default_provider_name = None

    def get_provider(self, name: str) -> FinancialStatementProvider:
        """Return a provider by name."""
        provider_name = self._normalize_provider_name(name)
        try:
            return self._providers[provider_name]
        except KeyError as error:
            raise KeyError(f"Unknown financial statement provider: {name}") from error

    def get_default_provider(self) -> FinancialStatementProvider:
        """Return the currently configured default provider."""
        if self._default_provider_name is None:
            raise KeyError("No default financial statement provider configured")
        return self.get_provider(self._default_provider_name)

    def set_default_provider(self, name: str) -> None:
        """Set the default provider by name."""
        provider_name = self._normalize_provider_name(name)
        if provider_name not in self._providers:
            raise KeyError(f"Unknown financial statement provider: {name}")
        self._default_provider_name = provider_name

    def list_providers(self) -> tuple[FinancialStatementProvider, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._providers.values())

    @staticmethod
    def _normalize_provider_name(name: str) -> str:
        return name.strip().lower()


__all__ = ["FinancialStatementProviderRegistry"]
