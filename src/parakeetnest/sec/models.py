"""Provider-agnostic SEC Filing Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class FilingType(str, Enum):
    """Supported provider-independent SEC filing form types."""

    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_S1 = "S-1"
    DEF_14A = "DEF 14A"
    FORM_4 = "Form 4"


@dataclass(frozen=True)
class SecFiling:
    """Normalized SEC filing metadata from any provider."""

    accession_number: str
    symbol: str
    company_name: str
    cik: str
    filing_type: FilingType
    filed_at: datetime
    report_date: date | None = None
    title: str | None = None
    filing_url: str | None = None
    document_url: str | None = None
    provider: str | None = None

    def __post_init__(self) -> None:
        """Normalize stable identity fields and validate filing type values."""
        object.__setattr__(self, "accession_number", self.accession_number.strip())
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "company_name", self.company_name.strip())
        object.__setattr__(self, "cik", self.cik.strip())
        if not isinstance(self.filing_type, FilingType):
            object.__setattr__(self, "filing_type", FilingType(self.filing_type))


@dataclass(frozen=True)
class SecFilingContent:
    """Provider-neutral filing text content for one SEC filing."""

    filing: SecFiling
    content: str
    source_url: str | None = None


@dataclass(frozen=True)
class SecFilingQuery:
    """Provider-neutral SEC filing search request."""

    symbols: list[str] | None = None
    filing_types: list[FilingType | str] | None = None
    limit: int = 10

    def __post_init__(self) -> None:
        """Normalize query fields used by providers."""
        if self.limit < 1:
            raise ValueError("limit must be at least 1")

        if self.symbols is not None:
            symbols = [
                symbol.strip().upper()
                for symbol in self.symbols
                if symbol.strip()
            ]
            object.__setattr__(self, "symbols", symbols)

        if self.filing_types is not None:
            filing_types = [
                filing_type
                if isinstance(filing_type, FilingType)
                else FilingType(filing_type)
                for filing_type in self.filing_types
            ]
            object.__setattr__(self, "filing_types", filing_types)


__all__ = [
    "FilingType",
    "SecFiling",
    "SecFilingContent",
    "SecFilingQuery",
]
