"""Tests for SecFilingContextProvider service-backed behavior."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from parakeetnest.context import ContextRequest, UnsupportedContextRequestError
from parakeetnest.context.providers import SecFilingContextProvider
from parakeetnest.sec import FilingType, SecFiling


class RecordingSecFilingService:
    """SEC filing service test double that records service-level requests."""

    def __init__(
        self,
        *,
        latest_10k: dict[str, SecFiling | None] | None = None,
        latest_10q: dict[str, SecFiling | None] | None = None,
        recent_8k: dict[str, list[SecFiling]] | None = None,
    ) -> None:
        self.latest_10k = latest_10k or {}
        self.latest_10q = latest_10q or {}
        self.recent_8k = recent_8k or {}
        self.calls: list[tuple[str, str, int | None]] = []

    def get_latest_10k(self, symbol: str) -> SecFiling | None:
        self.calls.append(("10-K", symbol, None))
        return self.latest_10k.get(symbol)

    def get_latest_10q(self, symbol: str) -> SecFiling | None:
        self.calls.append(("10-Q", symbol, None))
        return self.latest_10q.get(symbol)

    def get_recent_8k(self, symbol: str, limit: int = 5) -> list[SecFiling]:
        self.calls.append(("8-K", symbol, limit))
        return self.recent_8k.get(symbol, [])[:limit]


def _filing(
    symbol: str,
    filing_type: FilingType,
    accession_number: str,
    filed_at: datetime,
    title: str,
) -> SecFiling:
    return SecFiling(
        accession_number=accession_number,
        symbol=symbol,
        company_name=f"{symbol} Inc.",
        cik="0000000000",
        filing_type=filing_type,
        filed_at=filed_at,
        report_date=date(2026, 6, 29),
        title=title,
        filing_url=f"https://example.com/sec/{symbol.lower()}/{filing_type.value}",
        provider="mock",
    )


def test_sec_filing_context_provider_supports_symbol_requests_only() -> None:
    provider = SecFilingContextProvider(RecordingSecFilingService())

    assert provider.supports(ContextRequest("Review AMD.", ("AMD",))) is True
    assert provider.supports(ContextRequest("Review the market.", ())) is False


def test_sec_filing_context_provider_builds_filing_context_from_service() -> None:
    filed_10k = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    filed_10q = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    filed_8k = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    service = RecordingSecFilingService(
        latest_10k={
            "AMD": _filing(
                "AMD",
                FilingType.FORM_10K,
                "0000000000-26-000010",
                filed_10k,
                "AMD annual report",
            )
        },
        latest_10q={
            "AMD": _filing(
                "AMD",
                FilingType.FORM_10Q,
                "0000000000-26-000011",
                filed_10q,
                "AMD quarterly report",
            )
        },
        recent_8k={
            "AMD": [
                _filing(
                    "AMD",
                    FilingType.FORM_8K,
                    "0000000000-26-000012",
                    filed_8k,
                    "AMD current report",
                )
            ]
        },
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = SecFilingContextProvider(service).build_context(request)

    assert service.calls == [
        ("10-K", "AMD", None),
        ("10-Q", "AMD", None),
        ("8-K", "AMD", 3),
    ]
    assert result.provider_name == "sec_filings"
    assert result.metadata == {"source": "sec_filing_service"}
    assert result.partial_context.filings is not None
    assert result.partial_context.filings.source == "sec_filings"
    assert result.partial_context.filings.fetched_at == filed_8k
    assert [item.filing_type for item in result.partial_context.filings.items] == [
        "10-K",
        "10-Q",
        "8-K",
    ]
    assert result.partial_context.filings.items[0].summary == "AMD annual report"
    assert result.partial_context.filings.items[0].source == "mock"
    assert result.partial_context.filings.items[0].accession_number == (
        "0000000000-26-000010"
    )


def test_sec_filing_context_provider_rejects_requests_without_symbols() -> None:
    service = RecordingSecFilingService()
    provider = SecFilingContextProvider(service)
    request = ContextRequest(question="Review the market.", symbols=())

    with pytest.raises(UnsupportedContextRequestError):
        provider.build_context(request)

    assert service.calls == []


def test_sec_filing_context_provider_preserves_no_filings_result() -> None:
    service = RecordingSecFilingService()
    as_of = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    request = ContextRequest(
        question="Review POET.",
        symbols=("POET",),
        as_of=as_of,
    )

    result = SecFilingContextProvider(service).build_context(request)

    assert service.calls == [
        ("10-K", "POET", None),
        ("10-Q", "POET", None),
        ("8-K", "POET", 3),
    ]
    assert result.partial_context.filings is not None
    assert result.partial_context.filings.items == ()
    assert result.partial_context.filings.fetched_at == as_of
