"""Provider contract for SEC filing integrations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from parakeetnest.sec.models import SecFiling, SecFilingContent, SecFilingQuery


class SecFilingError(Exception):
    """Base class for provider-independent SEC filing failures."""


class SecFilingHttpError(SecFilingError):
    """Provider-independent error for SEC filing HTTP failures."""


class SecFilingParsingError(SecFilingError):
    """Provider-independent error for SEC filing response parsing failures."""


ProviderError = SecFilingError


@runtime_checkable
class SecFilingProvider(Protocol):
    """Small contract that all SEC filing providers must implement."""

    def search_filings(self, query: SecFilingQuery) -> list[SecFiling]:
        """Return provider-neutral SEC filings for the query."""
        ...

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        """Return provider-neutral filing content for an accession number."""
        ...


__all__ = [
    "ProviderError",
    "SecFilingError",
    "SecFilingHttpError",
    "SecFilingParsingError",
    "SecFilingProvider",
]
