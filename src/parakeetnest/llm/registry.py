"""Registry for configured LLM providers."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from parakeetnest.config import LLMConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.llm.mock import MockLLMProvider
from parakeetnest.llm.openai import OpenAIProvider
from parakeetnest.llm.provider import LLMProvider


LLMProviderFactory = Callable[[LLMConfig], LLMProvider]


@dataclass(frozen=True)
class LLMProviderRegistration:
    """A provider factory registered under a stable LLM provider ID."""

    provider_id: str
    factory: LLMProviderFactory


class LLMProviderRegistry:
    """Register and resolve LLM providers from configuration."""

    def __init__(self, *, default_provider_id: str = "mock") -> None:
        self._default_provider_id = self._normalize_provider_id(default_provider_id)
        self._registrations: dict[str, LLMProviderRegistration] = {}

    def register(self, provider_id: str, factory: LLMProviderFactory) -> None:
        """Register a provider factory under a unique provider ID."""
        normalized_provider_id = self._normalize_provider_id(provider_id)
        if normalized_provider_id in self._registrations:
            raise ValueError(f"LLM provider already registered: {normalized_provider_id}")
        self._registrations[normalized_provider_id] = LLMProviderRegistration(
            provider_id=normalized_provider_id,
            factory=factory,
        )

    def list_registrations(self) -> tuple[LLMProviderRegistration, ...]:
        """Return all registered providers in registration order."""
        return tuple(self._registrations.values())

    def resolve(self, config: LLMConfig) -> LLMProvider:
        """Create the provider selected by configuration."""
        normalized_provider_id = self._normalize_provider_id(config.provider)
        try:
            registration = self._registrations[normalized_provider_id]
        except KeyError as error:
            available_provider_ids = ", ".join(self._registrations) or "none"
            raise ConfigurationError(
                "Unknown LLM provider: "
                f"{config.provider}. Available providers: {available_provider_ids}"
            ) from error
        return registration.factory(config)

    def default(self) -> LLMProvider:
        """Return the configured default provider."""
        return self.resolve(LLMConfig(provider=self._default_provider_id))

    @staticmethod
    def _normalize_provider_id(provider_id: str) -> str:
        return provider_id.strip().lower()


def create_llm_provider_registry() -> LLMProviderRegistry:
    """Create the default LLM provider registry."""
    registry = LLMProviderRegistry(default_provider_id="mock")
    registry.register("mock", _create_mock_provider)
    registry.register("openai", _create_openai_provider)
    return registry


def _create_mock_provider(config: LLMConfig) -> LLMProvider:
    return MockLLMProvider(default_model=config.model)


def _create_openai_provider(config: LLMConfig) -> LLMProvider:
    api_key = os.environ.get(config.api_key_env_var)
    return OpenAIProvider(api_key=api_key, default_model=config.model)


__all__ = [
    "LLMProviderFactory",
    "LLMProviderRegistration",
    "LLMProviderRegistry",
    "create_llm_provider_registry",
]
