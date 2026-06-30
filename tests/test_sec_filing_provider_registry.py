"""Tests for SEC filing provider registration and configuration."""

from __future__ import annotations

import pytest

from parakeetnest.config import AppConfig, SecFilingConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.sec import (
    EdgarSecFilingProvider,
    MockSecFilingProvider,
    SecFiling,
    SecFilingContent,
    SecFilingProviderRegistry,
    SecFilingQuery,
    SecFilingService,
    create_sec_filing_provider_registry,
)


class RecordingSecFilingProvider:
    """SEC filing provider test double for registry lookups."""

    def __init__(self, provider_name: str = "recording") -> None:
        self.provider_name = provider_name

    def search_filings(self, query: SecFilingQuery) -> list[SecFiling]:
        """Return no filings; registry tests only need provider identity."""
        return []

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        """Registry tests do not exercise content lookup."""
        raise NotImplementedError


def test_registry_registers_and_gets_provider() -> None:
    registry = SecFilingProviderRegistry()
    provider = RecordingSecFilingProvider()

    registry.register("recording", provider)

    assert registry.get("recording") is provider
    assert [
        (registration.provider_id, registration.provider)
        for registration in registry.list_registrations()
    ] == [("recording", provider)]


def test_registry_normalizes_provider_ids() -> None:
    registry = SecFilingProviderRegistry()
    provider = RecordingSecFilingProvider()

    registry.register("  Mockish  ", provider)

    assert registry.get("MOCKISH") is provider


def test_registry_rejects_duplicate_registration() -> None:
    registry = SecFilingProviderRegistry()
    registry.register("mock", RecordingSecFilingProvider("first"))

    with pytest.raises(ValueError, match="SEC filing provider already registered: mock"):
        registry.register("MOCK", RecordingSecFilingProvider("second"))


def test_registry_unknown_provider_lookup_raises_clear_config_error() -> None:
    registry = create_sec_filing_provider_registry()

    with pytest.raises(ConfigurationError, match="Unknown SEC filing provider: missing"):
        registry.get("missing")


def test_default_sec_filing_provider_is_mock() -> None:
    config = AppConfig()
    registry = create_sec_filing_provider_registry()

    provider = registry.default()

    assert config.sec_filings == SecFilingConfig(provider="mock")
    assert isinstance(provider, MockSecFilingProvider)


def test_sec_filing_config_accepts_sec_edgar_user_agent_mapping() -> None:
    config = AppConfig(
        sec_filings={
            "provider": "sec_edgar",
            "sec_edgar_user_agent": "ParakeetNest tests test@example.com",
        }
    )

    assert config.sec_filings == SecFilingConfig(
        provider="sec_edgar",
        sec_edgar_user_agent="ParakeetNest tests test@example.com",
    )


def test_default_registry_includes_sec_edgar_provider() -> None:
    registry = create_sec_filing_provider_registry(
        sec_edgar_user_agent="ParakeetNest tests test@example.com"
    )

    provider = registry.get("sec_edgar")

    assert isinstance(provider, EdgarSecFilingProvider)


def test_selecting_configured_sec_filing_provider_works() -> None:
    registry = create_sec_filing_provider_registry()

    provider = registry.get("mock")
    service = SecFilingService(provider)

    filings = service.search_filings(SecFilingQuery(symbols=["AAPL"]))

    assert isinstance(provider, MockSecFilingProvider)
    assert filings[0].provider == "mock"
    assert filings[0].symbol == "AAPL"
