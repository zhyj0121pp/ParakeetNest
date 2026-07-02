"""Tests for the macro data provider registry."""

from __future__ import annotations

import pytest

from parakeetnest.config import MacroConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.macro import (
    FREDMacroProvider,
    MacroDataProviderRegistry,
    MockMacroDataProvider,
    create_macro_data_provider_registry,
)


def test_macro_provider_registry_defaults_include_mock_and_fred() -> None:
    """The default registry should expose deterministic and optional live providers."""
    registry = create_macro_data_provider_registry()

    assert [item.provider_id for item in registry.list_registrations()] == [
        "mock",
        "fred",
    ]


def test_macro_provider_registry_resolves_mock_by_default_config() -> None:
    """Mock macro data should remain the default provider."""
    registry = create_macro_data_provider_registry()

    provider = registry.resolve(MacroConfig())

    assert isinstance(provider, MockMacroDataProvider)


def test_macro_provider_registry_resolves_fred_from_config() -> None:
    """FRED should be available only through explicit macro provider config."""
    registry = create_macro_data_provider_registry()

    provider = registry.resolve(
        MacroConfig(provider="fred", fred_api_key_env_var="TEST_FRED_KEY", timeout=2.5)
    )

    assert isinstance(provider, FREDMacroProvider)
    assert provider._api_key_env_var == "TEST_FRED_KEY"
    assert provider._timeout_seconds == 2.5


def test_macro_provider_registry_rejects_unknown_provider() -> None:
    """Unknown provider IDs should fail with a provider-neutral config error."""
    registry = create_macro_data_provider_registry()

    with pytest.raises(ConfigurationError, match="Unknown macro data provider"):
        registry.resolve("missing")


def test_macro_provider_registry_rejects_duplicate_provider_ids() -> None:
    """Provider IDs should be unique after normalization."""
    registry = MacroDataProviderRegistry()
    registry.register("mock", lambda config: MockMacroDataProvider())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(" MOCK ", lambda config: MockMacroDataProvider())
