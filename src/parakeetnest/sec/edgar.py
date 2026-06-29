"""SEC EDGAR-backed filing provider."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, time
import json
from json import JSONDecodeError
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from parakeetnest.sec.models import (
    FilingType,
    SecFiling,
    SecFilingContent,
    SecFilingQuery,
)
from parakeetnest.sec.provider import (
    ProviderError,
    SecFilingHttpError,
    SecFilingParsingError,
)


HttpGet = Callable[[str, Mapping[str, str]], bytes]


class EdgarSecFilingProvider:
    """SEC filing provider backed by official EDGAR JSON endpoints."""

    provider_name = "sec_edgar"

    _COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    _SUBMISSIONS_BASE_URL = "https://data.sec.gov/submissions"
    _ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data"
    _SEC_FORM_TO_FILING_TYPE = {
        "10-K": FilingType.FORM_10K,
        "10-Q": FilingType.FORM_10Q,
        "8-K": FilingType.FORM_8K,
        "S-1": FilingType.FORM_S1,
        "DEF 14A": FilingType.DEF_14A,
        "4": FilingType.FORM_4,
        "FORM 4": FilingType.FORM_4,
    }

    def __init__(
        self,
        *,
        user_agent: str,
        http_get: HttpGet | None = None,
        timeout_seconds: float = 10.0,
        company_tickers_url: str = _COMPANY_TICKERS_URL,
        submissions_base_url: str = _SUBMISSIONS_BASE_URL,
        archives_base_url: str = _ARCHIVES_BASE_URL,
    ) -> None:
        """Initialize the provider with a SEC-compliant User-Agent."""
        normalized_user_agent = user_agent.strip()
        if not normalized_user_agent:
            raise ValueError("user_agent must not be blank")

        self._user_agent = normalized_user_agent
        self._http_get = http_get or self._default_http_get
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._company_tickers_url = company_tickers_url.rstrip("/")
        self._submissions_base_url = submissions_base_url.rstrip("/")
        self._archives_base_url = archives_base_url.rstrip("/")
        self._ticker_cik_lookup: dict[str, _TickerCik] | None = None

    def search_filings(self, query: SecFilingQuery) -> list[SecFiling]:
        """Return provider-neutral SEC filing metadata for ticker queries."""
        if not query.symbols:
            return []

        filings: list[SecFiling] = []
        wanted_types = set(query.filing_types or ())
        for symbol in query.symbols:
            ticker_cik = self._ticker_cik(symbol)
            if ticker_cik is None:
                continue
            submissions = self.get_company_submissions(ticker_cik.cik)
            filings.extend(
                self._filings_from_submissions(
                    submissions,
                    symbol=ticker_cik.ticker,
                    company_name=ticker_cik.company_name,
                    wanted_types=wanted_types,
                )
            )
            if len(filings) >= query.limit:
                break

        return filings[: query.limit]

    def get_company_submissions(self, cik: str) -> dict[str, Any]:
        """Return official SEC company submissions metadata for one CIK."""
        normalized_cik = self._normalize_cik(cik)
        url = f"{self._submissions_base_url}/CIK{normalized_cik}.json"
        payload = self._fetch_json(url)
        if not isinstance(payload, dict):
            raise SecFilingParsingError(
                f"SEC EDGAR submissions response was not an object for CIK {normalized_cik}."
            )
        return payload

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        """Full filing content retrieval is intentionally not implemented yet."""
        normalized_accession = accession_number.strip()
        raise ProviderError(
            "SEC EDGAR full filing content retrieval is not implemented yet "
            f"for accession number: {normalized_accession}"
        )

    def _ticker_cik(self, symbol: str) -> _TickerCik | None:
        lookup = self._ticker_cik_lookup
        if lookup is None:
            lookup = self._load_ticker_cik_lookup()
            self._ticker_cik_lookup = lookup
        return lookup.get(symbol.strip().upper())

    def _load_ticker_cik_lookup(self) -> dict[str, _TickerCik]:
        payload = self._fetch_json(self._company_tickers_url)
        if not isinstance(payload, dict):
            raise SecFilingParsingError("SEC EDGAR company tickers response was not an object.")

        lookup: dict[str, _TickerCik] = {}
        for raw_entry in payload.values():
            if not isinstance(raw_entry, dict):
                raise SecFilingParsingError(
                    "SEC EDGAR company tickers response included a non-object entry."
                )
            ticker = self._required_str(raw_entry, "ticker").upper()
            company_name = self._required_str(raw_entry, "title")
            cik = self._normalize_cik(raw_entry.get("cik_str"))
            lookup[ticker] = _TickerCik(
                ticker=ticker,
                cik=cik,
                company_name=company_name,
            )
        return lookup

    def _filings_from_submissions(
        self,
        submissions: dict[str, Any],
        *,
        symbol: str,
        company_name: str,
        wanted_types: set[FilingType],
    ) -> list[SecFiling]:
        recent = submissions.get("filings", {}).get("recent")
        if not isinstance(recent, dict):
            raise SecFilingParsingError("SEC EDGAR submissions response missing filings.recent.")

        forms = self._required_list(recent, "form")
        accessions = self._required_list(recent, "accessionNumber")
        filing_dates = self._required_list(recent, "filingDate")
        report_dates = self._optional_list(recent, "reportDate", len(forms))
        documents = self._optional_list(recent, "primaryDocument", len(forms))
        descriptions = self._optional_list(recent, "primaryDocDescription", len(forms))

        filings: list[SecFiling] = []
        cik = self._normalize_cik(submissions.get("cik"))
        for index, raw_form in enumerate(forms):
            filing_type = self._filing_type(raw_form)
            if filing_type is None:
                continue
            if wanted_types and filing_type not in wanted_types:
                continue

            accession_number = self._string_at(accessions, index, "accessionNumber")
            filed_on = self._date_at(filing_dates, index, "filingDate")
            primary_document = self._optional_string_at(documents, index)
            filing = SecFiling(
                accession_number=accession_number,
                symbol=symbol,
                company_name=company_name,
                cik=cik,
                filing_type=filing_type,
                filed_at=datetime.combine(filed_on, time.min, tzinfo=UTC),
                report_date=self._optional_date_at(report_dates, index),
                title=self._optional_string_at(descriptions, index),
                filing_url=self._filing_url(cik, accession_number),
                document_url=self._document_url(cik, accession_number, primary_document),
                provider=self.provider_name,
            )
            filings.append(filing)
        return filings

    def _fetch_json(self, url: str) -> Any:
        try:
            raw_body = self._http_get(url, self._headers())
        except HTTPError as error:
            raise SecFilingHttpError(
                f"SEC EDGAR HTTP request failed with status {error.code}: {url}"
            ) from error
        except (URLError, OSError) as error:
            raise SecFilingHttpError(f"SEC EDGAR HTTP request failed: {url}") from error
        except SecFilingHttpError:
            raise

        try:
            return json.loads(raw_body.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, JSONDecodeError) as error:
            raise SecFilingParsingError(
                f"SEC EDGAR returned malformed JSON: {url}"
            ) from error

    def _default_http_get(self, url: str, headers: Mapping[str, str]) -> bytes:
        request = Request(url, headers=dict(headers))
        with urlopen(request, timeout=self._timeout_seconds) as response:
            return response.read()

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

    def _filing_url(self, cik: str, accession_number: str) -> str:
        return (
            f"{self._archives_base_url}/{int(cik)}/"
            f"{accession_number.replace('-', '')}/{accession_number}-index.html"
        )

    def _document_url(
        self,
        cik: str,
        accession_number: str,
        primary_document: str | None,
    ) -> str | None:
        if primary_document is None:
            return None
        return (
            f"{self._archives_base_url}/{int(cik)}/"
            f"{accession_number.replace('-', '')}/{primary_document}"
        )

    def _filing_type(self, raw_form: Any) -> FilingType | None:
        form = str(raw_form).strip().upper()
        return self._SEC_FORM_TO_FILING_TYPE.get(form)

    def _normalize_cik(self, cik: Any) -> str:
        try:
            parsed = str(int(str(cik).strip()))
        except (TypeError, ValueError) as error:
            raise SecFilingParsingError(f"SEC EDGAR returned invalid CIK: {cik!r}") from error
        return parsed.zfill(10)

    def _required_list(self, payload: dict[str, Any], key: str) -> list[Any]:
        value = payload.get(key)
        if not isinstance(value, list):
            raise SecFilingParsingError(f"SEC EDGAR submissions missing list field: {key}")
        return value

    def _optional_list(
        self,
        payload: dict[str, Any],
        key: str,
        expected_length: int,
    ) -> list[Any]:
        value = payload.get(key)
        if value is None:
            return [None] * expected_length
        if not isinstance(value, list):
            raise SecFilingParsingError(f"SEC EDGAR submissions field was not a list: {key}")
        return value

    def _required_str(self, payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        parsed = str(value).strip() if value is not None else ""
        if not parsed:
            raise SecFilingParsingError(f"SEC EDGAR response missing string field: {key}")
        return parsed

    def _string_at(self, values: list[Any], index: int, key: str) -> str:
        try:
            value = values[index]
        except IndexError as error:
            raise SecFilingParsingError(
                f"SEC EDGAR submissions field length mismatch: {key}"
            ) from error
        parsed = str(value).strip() if value is not None else ""
        if not parsed:
            raise SecFilingParsingError(f"SEC EDGAR submissions had blank field: {key}")
        return parsed

    def _optional_string_at(self, values: list[Any], index: int) -> str | None:
        try:
            value = values[index]
        except IndexError:
            return None
        parsed = str(value).strip() if value is not None else ""
        return parsed or None

    def _date_at(self, values: list[Any], index: int, key: str) -> date:
        raw_value = self._string_at(values, index, key)
        try:
            return date.fromisoformat(raw_value)
        except ValueError as error:
            raise SecFilingParsingError(
                f"SEC EDGAR submissions had invalid date field: {key}"
            ) from error

    def _optional_date_at(self, values: list[Any], index: int) -> date | None:
        raw_value = self._optional_string_at(values, index)
        if raw_value is None:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError as error:
            raise SecFilingParsingError(
                "SEC EDGAR submissions had invalid reportDate field."
            ) from error


class _TickerCik:
    """Ticker lookup record loaded from SEC company_tickers.json."""

    def __init__(self, *, ticker: str, cik: str, company_name: str) -> None:
        self.ticker = ticker
        self.cik = cik
        self.company_name = company_name


__all__ = ["EdgarSecFilingProvider"]
