"""Tests for the provider-agnostic SEC filing service."""

from __future__ import annotations

from datetime import UTC, date, datetime

from parakeetnest.sec import (
    FilingType,
    MockSecFilingProvider,
    SecFiling,
    SecFilingContent,
    SecFilingProvider,
    SecFilingQuery,
    SecFilingService,
)


class SpySecFilingProvider:
    """Provider test double that records SEC filing service delegation."""

    def __init__(self) -> None:
        self.search_calls: list[SecFilingQuery] = []
        self.content_calls: list[str] = []
        self.filings = [
            SecFiling(
                accession_number="0000000001-26-000001",
                symbol="AMD",
                company_name="Advanced Micro Devices, Inc.",
                cik="0000000001",
                filing_type=FilingType.FORM_10K,
                filed_at=datetime(2026, 2, 15, 12, 0, tzinfo=UTC),
                report_date=date(2025, 12, 31),
                title="AMD annual report",
                provider="spy",
            )
        ]
        self.content = SecFilingContent(
            filing=self.filings[0],
            content="AMD annual report content.",
            source_url="https://example.com/sec/amd/10-k.txt",
        )

    def search_filings(self, query: SecFilingQuery) -> list[SecFiling]:
        """Record and return provider-backed filings."""
        self.search_calls.append(query)
        return self.filings

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        """Record and return provider-backed filing content."""
        self.content_calls.append(accession_number)
        return self.content


def test_search_filings_delegates_to_provider_once() -> None:
    provider = SpySecFilingProvider()
    service = SecFilingService(provider)
    query = SecFilingQuery(symbols=["amd"])

    service.search_filings(query)

    assert provider.search_calls == [query]


def test_search_filings_returns_exact_provider_result() -> None:
    provider = SpySecFilingProvider()
    service = SecFilingService(provider)

    filings = service.search_filings(SecFilingQuery())

    assert filings is provider.filings


def test_get_filing_content_delegates_to_provider() -> None:
    provider = SpySecFilingProvider()
    service = SecFilingService(provider)

    content = service.get_filing_content("0000000001-26-000001")

    assert provider.content_calls == ["0000000001-26-000001"]
    assert content is provider.content


def test_latest_10k_builds_provider_neutral_query() -> None:
    provider = SpySecFilingProvider()
    service = SecFilingService(provider)

    filing = service.get_latest_10k("amd")

    assert filing is provider.filings[0]
    assert provider.search_calls == [
        SecFilingQuery(
            symbols=["AMD"],
            filing_types=[FilingType.FORM_10K],
            limit=1,
        )
    ]


def test_latest_10q_builds_provider_neutral_query() -> None:
    provider = SpySecFilingProvider()
    service = SecFilingService(provider)

    service.get_latest_10q("nvda")

    assert provider.search_calls == [
        SecFilingQuery(
            symbols=["NVDA"],
            filing_types=[FilingType.FORM_10Q],
            limit=1,
        )
    ]


def test_latest_helpers_return_none_when_provider_has_no_match() -> None:
    provider = SpySecFilingProvider()
    provider.filings = []
    service = SecFilingService(provider)

    assert service.get_latest_10k("MSFT") is None


def test_recent_8k_builds_provider_neutral_query_with_limit() -> None:
    provider = SpySecFilingProvider()
    service = SecFilingService(provider)

    filings = service.get_recent_8k("tsla", limit=3)

    assert filings is provider.filings
    assert provider.search_calls == [
        SecFilingQuery(
            symbols=["TSLA"],
            filing_types=[FilingType.FORM_8K],
            limit=3,
        )
    ]


def test_service_works_with_mock_sec_filing_provider() -> None:
    provider: SecFilingProvider = MockSecFilingProvider()
    service = SecFilingService(provider)

    filing = service.get_latest_10k("AAPL")
    recent_8k = service.get_recent_8k("TSLA")

    assert filing is not None
    assert filing.accession_number == "0000320193-26-000010"
    assert recent_8k[0].filing_type is FilingType.FORM_8K
