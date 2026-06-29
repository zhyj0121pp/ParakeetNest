"""Provider-agnostic SEC filing service boundary."""

from __future__ import annotations

from parakeetnest.sec.models import (
    FilingType,
    SecFiling,
    SecFilingContent,
    SecFilingQuery,
)
from parakeetnest.sec.provider import SecFilingProvider


class SecFilingService:
    """Single entry point for provider-backed SEC filing requests."""

    def __init__(self, provider: SecFilingProvider) -> None:
        """Initialize the service with one SEC filing provider."""
        self._provider = provider

    def search_filings(self, query: SecFilingQuery) -> list[SecFiling]:
        """Return provider-backed SEC filing metadata for the query."""
        return self._provider.search_filings(query)

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        """Return provider-backed SEC filing content for an accession number."""
        return self._provider.get_filing_content(accession_number)

    def get_latest_10k(self, symbol: str) -> SecFiling | None:
        """Return the latest available annual report filing for the symbol."""
        return self._first_filing(symbol, FilingType.FORM_10K)

    def get_latest_10q(self, symbol: str) -> SecFiling | None:
        """Return the latest available quarterly report filing for the symbol."""
        return self._first_filing(symbol, FilingType.FORM_10Q)

    def get_recent_8k(self, symbol: str, limit: int = 5) -> list[SecFiling]:
        """Return recent current report filings for the symbol."""
        return self._provider.search_filings(
            SecFilingQuery(
                symbols=[symbol],
                filing_types=[FilingType.FORM_8K],
                limit=limit,
            )
        )

    def _first_filing(self, symbol: str, filing_type: FilingType) -> SecFiling | None:
        filings = self._provider.search_filings(
            SecFilingQuery(symbols=[symbol], filing_types=[filing_type], limit=1)
        )
        return filings[0] if filings else None


__all__ = ["SecFilingService"]
