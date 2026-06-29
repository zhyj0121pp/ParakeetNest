"""Tests for SEC Filing Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from parakeetnest.sec import FilingType, SecFiling, SecFilingContent, SecFilingQuery


def test_sec_filing_creation_normalizes_fields_and_is_immutable() -> None:
    """Filings should carry provider-neutral SEC metadata."""
    filed_at = datetime(2026, 1, 30, 12, 0, tzinfo=UTC)
    filing = SecFiling(
        accession_number=" 0000320193-26-000010 ",
        symbol=" aapl ",
        company_name=" Apple Inc. ",
        cik=" 0000320193 ",
        filing_type=FilingType.FORM_10K,
        filed_at=filed_at,
        report_date=date(2025, 12, 27),
        title="Apple Inc. annual report",
        filing_url="https://example.com/sec/aapl/10-k",
        document_url="https://example.com/sec/aapl/10-k.txt",
        provider="mock",
    )

    assert filing.accession_number == "0000320193-26-000010"
    assert filing.symbol == "AAPL"
    assert filing.company_name == "Apple Inc."
    assert filing.cik == "0000320193"
    assert filing.filing_type is FilingType.FORM_10K
    assert filing.filed_at == filed_at
    assert filing.report_date == date(2025, 12, 27)
    assert filing.title == "Apple Inc. annual report"
    assert filing.provider == "mock"

    with pytest.raises(FrozenInstanceError):
        filing.symbol = "MSFT"


def test_filing_type_values_are_provider_agnostic() -> None:
    """Supported filing types should expose stable SEC form values."""
    assert FilingType.FORM_10K.value == "10-K"
    assert FilingType.FORM_10Q.value == "10-Q"
    assert FilingType.FORM_8K.value == "8-K"
    assert FilingType.FORM_S1.value == "S-1"
    assert FilingType.DEF_14A.value == "DEF 14A"
    assert FilingType.FORM_4.value == "Form 4"


def test_invalid_filing_type_is_rejected() -> None:
    """Unknown filing types should fail at the domain boundary."""
    with pytest.raises(ValueError):
        FilingType("13F")

    with pytest.raises(ValueError):
        SecFiling(
            accession_number="0000000000-26-000001",
            symbol="TEST",
            company_name="Test Co.",
            cik="0000000000",
            filing_type="13F",
            filed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_sec_filing_query_defaults_and_normalization() -> None:
    """A query should default to a small provider-neutral request."""
    default_query = SecFilingQuery()
    filtered_query = SecFilingQuery(
        symbols=[" aapl ", "nvda"],
        filing_types=["10-K", FilingType.FORM_10Q],
        limit=5,
    )

    assert default_query.symbols is None
    assert default_query.filing_types is None
    assert default_query.limit == 10
    assert filtered_query.symbols == ["AAPL", "NVDA"]
    assert filtered_query.filing_types == [FilingType.FORM_10K, FilingType.FORM_10Q]
    assert filtered_query.limit == 5


def test_sec_filing_query_rejects_non_positive_limit() -> None:
    """Queries should keep provider requests bounded to positive result counts."""
    with pytest.raises(ValueError, match="limit must be at least 1"):
        SecFilingQuery(limit=0)


def test_sec_filing_content_creation() -> None:
    """Filing content should pair normalized metadata with provider-neutral text."""
    filing = SecFiling(
        accession_number="0001045810-26-000021",
        symbol="NVDA",
        company_name="NVIDIA Corporation",
        cik="0001045810",
        filing_type=FilingType.FORM_10Q,
        filed_at=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
    )
    content = SecFilingContent(
        filing=filing,
        content="NVIDIA Corporation quarterly report mock content.",
        source_url="https://example.com/sec/nvda/10-q.txt",
    )

    assert content.filing == filing
    assert content.content == "NVIDIA Corporation quarterly report mock content."
    assert content.source_url == "https://example.com/sec/nvda/10-q.txt"
