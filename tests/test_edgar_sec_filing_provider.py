"""Tests for the SEC EDGAR filing provider."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
import json
from urllib.error import HTTPError, URLError

import pytest

from parakeetnest.sec import (
    EdgarSecFilingProvider,
    FilingType,
    ProviderError,
    SecFilingHttpError,
    SecFilingParsingError,
    SecFilingProvider,
    SecFilingQuery,
)


class FakeHttpGet:
    """Byte-returning fake transport for mocked SEC endpoint responses."""

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> bytes:
        self.calls.append((url, dict(headers)))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        if isinstance(response, bytes):
            return response
        return json.dumps(response).encode("utf-8")


def test_edgar_provider_searches_filings_by_symbol_type_and_limit() -> None:
    transport = FakeHttpGet(
        {
            "https://www.sec.gov/files/company_tickers.json": {
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            },
            "https://data.sec.gov/submissions/CIK0000320193.json": _submissions_payload(),
        }
    )
    provider = EdgarSecFilingProvider(
        user_agent="ParakeetNest tests test@example.com",
        http_get=transport,
    )

    filings = provider.search_filings(
        SecFilingQuery(
            symbols=["aapl"],
            filing_types=[FilingType.FORM_10K, FilingType.FORM_8K],
            limit=1,
        )
    )

    assert len(filings) == 1
    assert filings[0].accession_number == "0000320193-26-000010"
    assert filings[0].symbol == "AAPL"
    assert filings[0].company_name == "Apple Inc."
    assert filings[0].cik == "0000320193"
    assert filings[0].filing_type is FilingType.FORM_10K
    assert filings[0].filed_at == datetime(2026, 1, 30, tzinfo=UTC)
    assert filings[0].report_date == date(2025, 12, 27)
    assert filings[0].title == "Annual report"
    assert filings[0].filing_url == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019326000010/0000320193-26-000010-index.html"
    )
    assert filings[0].document_url == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019326000010/aapl-20251227.htm"
    )
    assert filings[0].provider == "edgar"


def test_edgar_provider_sends_configured_user_agent_to_all_sec_endpoints() -> None:
    transport = FakeHttpGet(
        {
            "https://www.sec.gov/files/company_tickers.json": {
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            },
            "https://data.sec.gov/submissions/CIK0000320193.json": _submissions_payload(),
        }
    )
    provider = EdgarSecFilingProvider(
        user_agent="Research App contact@example.com",
        http_get=transport,
    )

    provider.search_filings(SecFilingQuery(symbols=["AAPL"]))

    assert [call[1]["User-Agent"] for call in transport.calls] == [
        "Research App contact@example.com",
        "Research App contact@example.com",
    ]
    assert all(call[1]["Accept"] == "application/json" for call in transport.calls)


def test_edgar_provider_supports_company_submissions_lookup_by_cik() -> None:
    transport = FakeHttpGet(
        {
            "https://data.sec.gov/submissions/CIK0000320193.json": _submissions_payload(
                cik="320193"
            )
        }
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    submissions = provider.get_company_submissions("320193")

    assert submissions["cik"] == "320193"
    assert transport.calls[0][0] == "https://data.sec.gov/submissions/CIK0000320193.json"


def test_edgar_provider_returns_empty_results_for_unknown_symbols() -> None:
    transport = FakeHttpGet(
        {
            "https://www.sec.gov/files/company_tickers.json": {
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            },
        }
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    assert provider.search_filings(SecFilingQuery(symbols=["MSFT"])) == []
    assert len(transport.calls) == 1


def test_edgar_provider_returns_empty_results_without_symbols() -> None:
    provider = EdgarSecFilingProvider(
        user_agent="tests",
        http_get=FakeHttpGet({}),
    )

    assert provider.search_filings(SecFilingQuery()) == []


def test_edgar_provider_maps_sec_form_4_to_provider_neutral_filing_type() -> None:
    transport = FakeHttpGet(
        {
            "https://www.sec.gov/files/company_tickers.json": {
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            },
            "https://data.sec.gov/submissions/CIK0000320193.json": _submissions_payload(),
        }
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    filings = provider.search_filings(
        SecFilingQuery(symbols=["AAPL"], filing_types=[FilingType.FORM_4])
    )

    assert [filing.filing_type for filing in filings] == [FilingType.FORM_4]
    assert filings[0].accession_number == "0000320193-26-000012"


def test_edgar_provider_does_not_fetch_full_filing_content_yet() -> None:
    provider = EdgarSecFilingProvider(
        user_agent="tests",
        http_get=FakeHttpGet({}),
    )

    with pytest.raises(ProviderError, match="not implemented yet"):
        provider.get_filing_content("0000320193-26-000010")


def test_edgar_provider_maps_http_failures_to_provider_neutral_error() -> None:
    transport = FakeHttpGet(
        {
            "https://data.sec.gov/submissions/CIK0000320193.json": HTTPError(
                "https://data.sec.gov/submissions/CIK0000320193.json",
                503,
                "Service Unavailable",
                hdrs=None,
                fp=None,
            )
        }
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    with pytest.raises(SecFilingHttpError, match="status 503"):
        provider.get_company_submissions("0000320193")


def test_edgar_provider_maps_timeout_to_provider_neutral_error() -> None:
    transport = FakeHttpGet(
        {
            "https://data.sec.gov/submissions/CIK0000320193.json": URLError(
                TimeoutError("timed out")
            )
        }
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    with pytest.raises(SecFilingHttpError, match="HTTP request failed"):
        provider.get_company_submissions("0000320193")


def test_edgar_provider_maps_malformed_json_to_provider_neutral_error() -> None:
    transport = FakeHttpGet(
        {"https://data.sec.gov/submissions/CIK0000320193.json": b"not json"}
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    with pytest.raises(SecFilingParsingError, match="malformed JSON"):
        provider.get_company_submissions("0000320193")


def test_edgar_provider_rejects_malformed_submission_payloads() -> None:
    transport = FakeHttpGet(
        {
            "https://www.sec.gov/files/company_tickers.json": {
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            },
            "https://data.sec.gov/submissions/CIK0000320193.json": {"cik": 320193},
        }
    )
    provider = EdgarSecFilingProvider(user_agent="tests", http_get=transport)

    with pytest.raises(SecFilingParsingError, match="filings.recent"):
        provider.search_filings(SecFilingQuery(symbols=["AAPL"]))


def test_edgar_provider_satisfies_sec_filing_provider_protocol() -> None:
    provider: SecFilingProvider = EdgarSecFilingProvider(
        user_agent="tests",
        http_get=FakeHttpGet({}),
    )

    assert isinstance(provider, SecFilingProvider)


def _submissions_payload(cik: str = "0000320193") -> dict[str, object]:
    return {
        "cik": cik,
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0000320193-26-000010",
                    "0000320193-26-000011",
                    "0000320193-26-000012",
                ],
                "filingDate": ["2026-01-30", "2026-02-02", "2026-02-03"],
                "reportDate": ["2025-12-27", "2026-02-02", "2026-02-03"],
                "form": ["10-K", "8-K", "4"],
                "primaryDocument": [
                    "aapl-20251227.htm",
                    "aapl-8k.htm",
                    "xslF345X05/wk-form4_123.xml",
                ],
                "primaryDocDescription": [
                    "Annual report",
                    "Current report",
                    "Insider ownership filing",
                ],
            }
        },
    }
