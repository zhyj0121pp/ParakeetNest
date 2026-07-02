"""FRED-backed macroeconomic data provider."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
import json
from json import JSONDecodeError
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from parakeetnest.macro.models import (
    MacroCategory,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)
from parakeetnest.macro.provider import (
    MacroDataConfigurationError,
    MacroDataHttpError,
    MacroDataParsingError,
    MacroDataProvider,
)


HttpGet = Callable[[str, float], bytes]


@dataclass(frozen=True)
class FredSeriesMapping:
    """Provider-neutral metadata and FRED lookup settings for one indicator."""

    indicator_id: str
    fred_series_id: str
    name: str
    category: MacroCategory
    frequency: MacroFrequency
    unit: MacroUnit
    region: str = "US"
    description: str | None = None
    fred_units: str | None = None

    def indicator(self) -> MacroIndicator:
        """Return provider-neutral metadata for this mapping."""
        return MacroIndicator(
            indicator_id=self.indicator_id,
            name=self.name,
            category=self.category,
            frequency=self.frequency,
            unit=self.unit,
            region=self.region,
            description=self.description,
        )


class FREDMacroProvider(MacroDataProvider):
    """Macro provider backed by the Federal Reserve Economic Data API."""

    provider_name = "fred"

    _API_BASE_URL = "https://api.stlouisfed.org/fred"
    _DEFAULT_MAPPINGS = (
        FredSeriesMapping(
            indicator_id="fed_funds_rate",
            fred_series_id="FEDFUNDS",
            name="Federal Funds Effective Rate",
            category=MacroCategory.RATES,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            description="Effective federal funds rate from FRED.",
        ),
        FredSeriesMapping(
            indicator_id="treasury_10y_yield",
            fred_series_id="DGS10",
            name="10-Year Treasury Constant Maturity Rate",
            category=MacroCategory.RATES,
            frequency=MacroFrequency.DAILY,
            unit=MacroUnit.PERCENT,
            description="10-year Treasury yield from FRED.",
        ),
        FredSeriesMapping(
            indicator_id="treasury_2y_yield",
            fred_series_id="DGS2",
            name="2-Year Treasury Constant Maturity Rate",
            category=MacroCategory.RATES,
            frequency=MacroFrequency.DAILY,
            unit=MacroUnit.PERCENT,
            description="2-year Treasury yield from FRED.",
        ),
        FredSeriesMapping(
            indicator_id="cpi_yoy",
            fred_series_id="CPIAUCSL",
            name="Consumer Price Index Year-over-Year",
            category=MacroCategory.INFLATION,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            description="Headline CPI percent change from one year ago via FRED.",
            fred_units="pc1",
        ),
        FredSeriesMapping(
            indicator_id="unemployment_rate",
            fred_series_id="UNRATE",
            name="Unemployment Rate",
            category=MacroCategory.LABOR,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            description="Civilian unemployment rate from FRED.",
        ),
        FredSeriesMapping(
            indicator_id="nonfarm_payrolls",
            fred_series_id="PAYEMS",
            name="All Employees, Total Nonfarm",
            category=MacroCategory.LABOR,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.THOUSANDS,
            description="Total nonfarm payroll employment level from FRED.",
        ),
        FredSeriesMapping(
            indicator_id="gdp_growth",
            fred_series_id="GDP",
            name="Gross Domestic Product Year-over-Year",
            category=MacroCategory.GROWTH,
            frequency=MacroFrequency.QUARTERLY,
            unit=MacroUnit.PERCENT,
            description="Gross domestic product percent change from one year ago via FRED.",
            fred_units="pc1",
        ),
    )

    def __init__(
        self,
        *,
        api_key_env_var: str = "FRED_API_KEY",
        environ: Mapping[str, str] | None = None,
        http_get: HttpGet | None = None,
        timeout_seconds: float = 10.0,
        api_base_url: str = _API_BASE_URL,
        mappings: tuple[FredSeriesMapping, ...] | None = None,
    ) -> None:
        """Initialize the provider from an environment-sourced API key."""
        self._api_key_env_var = api_key_env_var.strip() or "FRED_API_KEY"
        self._environ = environ if environ is not None else os.environ
        self._http_get = http_get or self._default_http_get
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._api_base_url = api_base_url.rstrip("/")
        self._mappings = self._build_mappings(mappings or self._DEFAULT_MAPPINGS)

    def get_series(
        self,
        indicator_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MacroSeries:
        """Return normalized FRED observations for a provider-neutral indicator."""
        mapping = self._mapping_for(indicator_id)
        if mapping is None:
            normalized_id = self._normalize_indicator_id(indicator_id)
            return MacroSeries(indicator=self._unknown_indicator(normalized_id))

        payload = self._fetch_json(
            "series/observations",
            self._observation_params(mapping, start_date, end_date),
        )
        observations = payload.get("observations")
        if not isinstance(observations, list):
            raise MacroDataParsingError(
                f"FRED observations response missing observations for {mapping.fred_series_id}."
            )

        return MacroSeries(
            indicator=mapping.indicator(),
            observations=[
                self._parse_observation(raw_observation, mapping.fred_series_id)
                for raw_observation in observations
            ],
        )

    def get_latest(self, indicator_id: str) -> MacroObservation | None:
        """Return the latest available FRED observation for an indicator."""
        series = self.get_series(indicator_id)
        if not series.observations:
            return None
        return series.observations[-1]

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Return a provider-neutral snapshot backed by FRED observations."""
        snapshot_date = as_of_date or date.today()
        return MacroSnapshot(
            as_of_date=snapshot_date,
            series=[
                self.get_series(indicator_id, end_date=snapshot_date)
                for indicator_id in indicator_ids
            ],
        )

    def _observation_params(
        self,
        mapping: FredSeriesMapping,
        start_date: date | None,
        end_date: date | None,
    ) -> dict[str, str]:
        params = {
            "series_id": mapping.fred_series_id,
            "sort_order": "asc",
        }
        if mapping.fred_units is not None:
            params["units"] = mapping.fred_units
        if start_date is not None:
            params["observation_start"] = start_date.isoformat()
        if end_date is not None:
            params["observation_end"] = end_date.isoformat()
        return params

    def _fetch_json(self, path: str, params: Mapping[str, str]) -> dict[str, Any]:
        request_params = {
            "api_key": self._api_key(),
            "file_type": "json",
            **dict(params),
        }
        url = f"{self._api_base_url}/{path}?{urlencode(request_params)}"
        try:
            raw_body = self._http_get(url, self._timeout_seconds)
        except HTTPError as error:
            raise MacroDataHttpError(
                f"FRED HTTP request failed with status {error.code}: {path}"
            ) from error
        except (TimeoutError, URLError, OSError) as error:
            raise MacroDataHttpError(f"FRED HTTP request failed: {path}") from error
        except MacroDataHttpError:
            raise

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, JSONDecodeError) as error:
            raise MacroDataParsingError(f"FRED returned malformed JSON: {path}") from error
        if not isinstance(payload, dict):
            raise MacroDataParsingError(f"FRED returned a non-object payload: {path}")
        if isinstance(payload.get("error_message"), str):
            raise MacroDataHttpError(f"FRED API error: {payload['error_message']}")
        return payload

    def _api_key(self) -> str:
        api_key = self._environ.get(self._api_key_env_var, "").strip()
        if not api_key:
            raise MacroDataConfigurationError(
                f"FRED macro provider requires environment variable {self._api_key_env_var}."
            )
        return api_key

    def _default_http_get(self, url: str, timeout_seconds: float) -> bytes:
        with urlopen(url, timeout=timeout_seconds) as response:
            return response.read()

    def _parse_observation(
        self,
        raw_observation: Any,
        fred_series_id: str,
    ) -> MacroObservation:
        if not isinstance(raw_observation, dict):
            raise MacroDataParsingError(
                f"FRED observation for {fred_series_id} was not an object."
            )
        raw_date = raw_observation.get("date")
        if not isinstance(raw_date, str):
            raise MacroDataParsingError(
                f"FRED observation for {fred_series_id} missing date."
            )
        try:
            period = date.fromisoformat(raw_date)
        except ValueError as error:
            raise MacroDataParsingError(
                f"FRED observation for {fred_series_id} had invalid date: {raw_date!r}."
            ) from error

        raw_value = raw_observation.get("value")
        if raw_value is None or raw_value == ".":
            value = None
        else:
            try:
                value = float(str(raw_value))
            except ValueError as error:
                raise MacroDataParsingError(
                    f"FRED observation for {fred_series_id} had invalid value: {raw_value!r}."
                ) from error
        return MacroObservation(period=period, value=value)

    def _mapping_for(self, indicator_id: str) -> FredSeriesMapping | None:
        return self._mappings.get(self._normalize_indicator_id(indicator_id))

    def _build_mappings(
        self,
        mappings: tuple[FredSeriesMapping, ...],
    ) -> dict[str, FredSeriesMapping]:
        lookup: dict[str, FredSeriesMapping] = {}
        for mapping in mappings:
            lookup[self._normalize_indicator_id(mapping.indicator_id)] = mapping
            lookup[self._normalize_indicator_id(mapping.fred_series_id)] = mapping
        return lookup

    def _unknown_indicator(self, indicator_id: str) -> MacroIndicator:
        fallback_id = indicator_id or "unknown_indicator"
        return MacroIndicator(
            indicator_id=fallback_id,
            name=fallback_id.replace("_", " ").title(),
            category=MacroCategory.OTHER,
            frequency=MacroFrequency.IRREGULAR,
            unit=MacroUnit.OTHER,
        )

    @staticmethod
    def _normalize_indicator_id(indicator_id: str) -> str:
        return indicator_id.strip().lower()


__all__ = ["FREDMacroProvider", "FredSeriesMapping", "HttpGet"]
