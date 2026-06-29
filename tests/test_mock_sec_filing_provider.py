"""Tests for the deterministic mock SEC filing provider."""

from __future__ import annotations

import pytest

from parakeetnest.sec import (
    FilingType,
    MockSecFilingProvider,
    ProviderError,
    SecFiling,
    SecFilingProvider,
    SecFilingQuery,
)


def test_mock_provider_returns_deterministic_filings() -> None:
    """Repeated calls and provider instances should return identical filings."""
    first_provider = MockSecFilingProvider()
    second_provider = MockSecFilingProvider()

    first_filings = first_provider.search_filings(SecFilingQuery())
    second_filings = second_provider.search_filings(SecFilingQuery())

    assert first_filings == second_filings
    assert len(first_filings) == 6
    assert all(isinstance(filing, SecFiling) for filing in first_filings)
    assert first_filings[0].symbol == "AAPL"
    assert first_filings[0].filing_type is FilingType.FORM_10K


def test_mock_provider_includes_required_symbols_and_filing_types() -> None:
    """The mock provider should cover the Epic 7.1 deterministic fixture set."""
    provider = MockSecFilingProvider()

    filings = provider.search_filings(SecFilingQuery())

    assert {filing.symbol for filing in filings} == {"AAPL", "NVDA", "TSLA"}
    assert {filing.filing_type for filing in filings} == {
        FilingType.FORM_10K,
        FilingType.FORM_10Q,
        FilingType.FORM_8K,
        FilingType.FORM_S1,
        FilingType.DEF_14A,
        FilingType.FORM_4,
    }


def test_mock_provider_applies_limit() -> None:
    """The mock provider should honor the provider-neutral query limit."""
    provider = MockSecFilingProvider()

    filings = provider.search_filings(SecFilingQuery(limit=2))

    assert [filing.accession_number for filing in filings] == [
        "0000320193-26-000010",
        "0000320193-26-000042",
    ]


def test_mock_provider_filters_by_symbol() -> None:
    """Symbol filtering should match normalized filing symbols."""
    provider = MockSecFilingProvider()

    filings = provider.search_filings(SecFilingQuery(symbols=["nvda"]))

    assert len(filings) == 2
    assert {filing.symbol for filing in filings} == {"NVDA"}
    assert {filing.filing_type for filing in filings} == {
        FilingType.FORM_10Q,
        FilingType.FORM_4,
    }


def test_mock_provider_filters_by_filing_type() -> None:
    """Filing type filtering should match provider-neutral enum values."""
    provider = MockSecFilingProvider()

    filings = provider.search_filings(
        SecFilingQuery(filing_types=[FilingType.FORM_8K, "S-1"]),
    )

    assert [filing.symbol for filing in filings] == ["TSLA", "TSLA"]
    assert [filing.filing_type for filing in filings] == [
        FilingType.FORM_8K,
        FilingType.FORM_S1,
    ]


def test_mock_provider_combines_symbol_and_filing_type_filters() -> None:
    """Symbol and filing type filters should narrow results together."""
    provider = MockSecFilingProvider()

    filings = provider.search_filings(
        SecFilingQuery(symbols=["AAPL", "TSLA"], filing_types=["10-K"]),
    )

    assert len(filings) == 1
    assert filings[0].symbol == "AAPL"
    assert filings[0].filing_type is FilingType.FORM_10K


def test_get_filing_content_returns_matching_filing_and_text() -> None:
    """Content lookup should return deterministic text for one accession."""
    provider = MockSecFilingProvider()

    content = provider.get_filing_content(" 0001045810-26-000021 ")

    assert content.filing.symbol == "NVDA"
    assert content.filing.filing_type is FilingType.FORM_10Q
    assert "quarterly report" in content.content
    assert "data center demand" in content.content
    assert content.source_url == content.filing.document_url


def test_get_filing_content_rejects_unknown_accession() -> None:
    """Unsupported accessions should fail with the provider-neutral error type."""
    provider = MockSecFilingProvider()

    with pytest.raises(
        ProviderError,
        match="Unsupported accession number: 0000000000-26-000001",
    ):
        provider.get_filing_content("0000000000-26-000001")


def test_mock_provider_returns_fresh_lists() -> None:
    """Mutating returned lists should not affect later calls."""
    provider = MockSecFilingProvider()

    filings = provider.search_filings(SecFilingQuery())
    filings.clear()

    assert len(provider.search_filings(SecFilingQuery())) == 6


def test_mock_provider_satisfies_sec_filing_provider_protocol() -> None:
    """The mock provider should be usable through the provider protocol."""
    provider: SecFilingProvider = MockSecFilingProvider()

    assert isinstance(provider, SecFilingProvider)
    assert provider.search_filings(SecFilingQuery(symbols=["AAPL"]))[0].cik == (
        "0000320193"
    )
    assert provider.get_filing_content("0000320193-26-000010").filing.symbol == "AAPL"
