"""Deterministic in-memory SEC filing provider."""

from __future__ import annotations

from datetime import UTC, date, datetime

from parakeetnest.sec.models import (
    FilingType,
    SecFiling,
    SecFilingContent,
    SecFilingQuery,
)
from parakeetnest.sec.provider import ProviderError


class MockSecFilingProvider:
    """SEC filing provider backed by embedded deterministic fixtures."""

    _FILINGS = (
        SecFiling(
            accession_number="0000320193-26-000010",
            symbol="AAPL",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type=FilingType.FORM_10K,
            filed_at=datetime(2026, 1, 30, 12, 0, tzinfo=UTC),
            report_date=date(2025, 12, 27),
            title="Apple Inc. annual report",
            filing_url="https://example.com/sec/aapl/10-k",
            document_url="https://example.com/sec/aapl/10-k.txt",
            provider="mock",
        ),
        SecFiling(
            accession_number="0000320193-26-000042",
            symbol="AAPL",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type=FilingType.DEF_14A,
            filed_at=datetime(2026, 3, 5, 12, 0, tzinfo=UTC),
            report_date=date(2026, 3, 5),
            title="Apple Inc. proxy statement",
            filing_url="https://example.com/sec/aapl/def-14a",
            document_url="https://example.com/sec/aapl/def-14a.txt",
            provider="mock",
        ),
        SecFiling(
            accession_number="0001045810-26-000021",
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            cik="0001045810",
            filing_type=FilingType.FORM_10Q,
            filed_at=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
            report_date=date(2026, 4, 26),
            title="NVIDIA Corporation quarterly report",
            filing_url="https://example.com/sec/nvda/10-q",
            document_url="https://example.com/sec/nvda/10-q.txt",
            provider="mock",
        ),
        SecFiling(
            accession_number="0001045810-26-000030",
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            cik="0001045810",
            filing_type=FilingType.FORM_4,
            filed_at=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
            report_date=date(2026, 6, 10),
            title="NVIDIA Corporation insider ownership filing",
            filing_url="https://example.com/sec/nvda/form-4",
            document_url="https://example.com/sec/nvda/form-4.txt",
            provider="mock",
        ),
        SecFiling(
            accession_number="0001318605-26-000007",
            symbol="TSLA",
            company_name="Tesla, Inc.",
            cik="0001318605",
            filing_type=FilingType.FORM_8K,
            filed_at=datetime(2026, 4, 20, 12, 0, tzinfo=UTC),
            report_date=date(2026, 4, 20),
            title="Tesla, Inc. current report",
            filing_url="https://example.com/sec/tsla/8-k",
            document_url="https://example.com/sec/tsla/8-k.txt",
            provider="mock",
        ),
        SecFiling(
            accession_number="0001318605-26-000015",
            symbol="TSLA",
            company_name="Tesla, Inc.",
            cik="0001318605",
            filing_type=FilingType.FORM_S1,
            filed_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            report_date=date(2026, 6, 1),
            title="Tesla, Inc. registration statement",
            filing_url="https://example.com/sec/tsla/s-1",
            document_url="https://example.com/sec/tsla/s-1.txt",
            provider="mock",
        ),
    )

    _CONTENT = {
        "0000320193-26-000010": (
            "Apple Inc. annual report. Mock SEC filing content covering revenue, "
            "services growth, product risk, capital allocation, and supply chain "
            "considerations."
        ),
        "0000320193-26-000042": (
            "Apple Inc. proxy statement. Mock SEC filing content covering board "
            "matters, executive compensation, shareholder votes, and governance."
        ),
        "0001045810-26-000021": (
            "NVIDIA Corporation quarterly report. Mock SEC filing content covering "
            "data center demand, gross margin, inventory risk, and AI accelerator "
            "supply."
        ),
        "0001045810-26-000030": (
            "NVIDIA Corporation Form 4. Mock SEC filing content covering insider "
            "transaction details and reported ownership changes."
        ),
        "0001318605-26-000007": (
            "Tesla, Inc. current report. Mock SEC filing content covering a "
            "material corporate update, operational context, and risk factors."
        ),
        "0001318605-26-000015": (
            "Tesla, Inc. registration statement. Mock SEC filing content covering "
            "securities registration, use of proceeds, dilution, and business risks."
        ),
    }

    def search_filings(self, query: SecFilingQuery) -> list[SecFiling]:
        """Return deterministic filings matching symbols and filing types."""
        filings = list(self._FILINGS)

        if query.symbols:
            wanted_symbols = set(query.symbols)
            filings = [
                filing for filing in filings if filing.symbol in wanted_symbols
            ]

        if query.filing_types:
            wanted_types = set(query.filing_types)
            filings = [
                filing for filing in filings if filing.filing_type in wanted_types
            ]

        return filings[: query.limit]

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        """Return deterministic filing content for an accession number."""
        normalized_accession = accession_number.strip()
        filing = self._filing_by_accession(normalized_accession)
        try:
            content = self._CONTENT[normalized_accession]
        except KeyError as exc:
            raise ProviderError(
                f"Unsupported accession number: {normalized_accession}"
            ) from exc

        return SecFilingContent(
            filing=filing,
            content=content,
            source_url=filing.document_url,
        )

    def _filing_by_accession(self, accession_number: str) -> SecFiling:
        for filing in self._FILINGS:
            if filing.accession_number == accession_number:
                return filing
        raise ProviderError(f"Unsupported accession number: {accession_number}")


__all__ = ["MockSecFilingProvider"]
