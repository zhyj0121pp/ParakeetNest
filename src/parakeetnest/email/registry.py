"""Registry for configured email providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from parakeetnest.config import EmailConfig
from parakeetnest.email.gmail_provider import GmailEmailProvider
from parakeetnest.email.mock_provider import MockEmailProvider
from parakeetnest.email.provider import EmailProvider
from parakeetnest.exceptions import ConfigurationError


EmailProviderFactory = Callable[[EmailConfig], EmailProvider]


@dataclass(frozen=True)
class EmailProviderRegistration:
    """A provider factory registered under a stable email provider ID."""

    provider_id: str
    factory: EmailProviderFactory


class EmailProviderRegistry:
    """Register and resolve email providers from configuration."""

    def __init__(self, *, default_provider_id: str = "mock") -> None:
        self._default_provider_id = self._normalize_provider_id(default_provider_id)
        self._registrations: dict[str, EmailProviderRegistration] = {}

    def register(self, provider_id: str, factory: EmailProviderFactory) -> None:
        """Register a provider factory under a unique provider ID."""
        normalized_provider_id = self._normalize_provider_id(provider_id)
        if normalized_provider_id in self._registrations:
            raise ValueError(f"Email provider already registered: {normalized_provider_id}")
        self._registrations[normalized_provider_id] = EmailProviderRegistration(
            provider_id=normalized_provider_id,
            factory=factory,
        )

    def list_registrations(self) -> tuple[EmailProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def resolve(self, config: EmailConfig | str) -> EmailProvider:
        """Create the provider selected by configuration."""
        resolved_config = self._resolve_config(config)
        normalized_provider_id = self._normalize_provider_id(resolved_config.provider)
        try:
            registration = self._registrations[normalized_provider_id]
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown email provider: "
                f"{resolved_config.provider}. Available providers: {available_provider_ids}"
            ) from error
        return registration.factory(resolved_config)

    def default(self) -> EmailProvider:
        """Return the configured default provider."""
        return self.resolve(EmailConfig(provider=self._default_provider_id))

    @staticmethod
    def _normalize_provider_id(provider_id: str) -> str:
        return provider_id.strip().lower()

    @staticmethod
    def _resolve_config(config: EmailConfig | str) -> EmailConfig:
        if isinstance(config, EmailConfig):
            return config
        return EmailConfig(provider=config)


def create_email_provider_registry() -> EmailProviderRegistry:
    """Create the default email provider registry."""
    registry = EmailProviderRegistry(default_provider_id="mock")
    registry.register("mock", _create_mock_provider)
    registry.register("gmail", _create_gmail_provider)
    return registry


def _create_mock_provider(config: EmailConfig) -> EmailProvider:
    return MockEmailProvider()


def _create_gmail_provider(config: EmailConfig) -> EmailProvider:
    return GmailEmailProvider(
        credentials_path_env_var=config.gmail_credentials_path_env_var,
        token_path_env_var=config.gmail_token_path_env_var,
        sender_email=config.sender_email,
    )


__all__ = [
    "EmailProviderFactory",
    "EmailProviderRegistration",
    "EmailProviderRegistry",
    "create_email_provider_registry",
]
