"""Tests for the FRED macro data provider."""

from __future__ import annotations

from datetime import date
import json
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from parakeetnest.macro import (
    FREDMacroProvider,
    MacroCategory,
    MacroDataConfigurationError,
    MacroDataHttpError,
    MacroDataParsingError,
    MacroDataProvider,
    MacroFrequency,
    MacroObservation,
    MacroSeries,
    MacroUnit,
)


class FakeHttpGet:
    """Byte-returning fake transport for mocked FRED endpoint responses."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, float]] = []

    def __call__(self, url: str, timeout_seconds: float) -> bytes:
        self.calls.append((url, timeout_seconds))
        if isinstance(self.response, Exception):
            raise self.response
        if isinstance(self.response, bytes):
            return self.response
        return json.dumps(self.response).encode("utf-8")

    @property
    def query(self) -> dict[str, list[str]]:
        assert self.calls
        return parse_qs(urlparse(self.calls[0][0]).query)


def test_fred_provider_fetches_series_with_env_api_key_and_date_filters() -> None:
    transport = FakeHttpGet(
        {
            "observations": [
                {"date": "2026-05-01", "value": "4.33"},
                {"date": "2026-05-02", "value": "."},
            ]
        }
    )
    provider = FREDMacroProvider(
        environ={"TEST_FRED_KEY": "secret"},
        api_key_env_var="TEST_FRED_KEY",
        http_get=transport,
        timeout_seconds=2.5,
    )

    series = provider.get_series(
        "FEDFUNDS",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    assert isinstance(series, MacroSeries)
    assert series.indicator.indicator_id == "fed_funds_rate"
    assert series.indicator.category is MacroCategory.RATES
    assert series.indicator.frequency is MacroFrequency.MONTHLY
    assert series.indicator.unit is MacroUnit.PERCENT
    assert [observation.period for observation in series.observations] == [
        date(2026, 5, 1),
        date(2026, 5, 2),
    ]
    assert [observation.value for observation in series.observations] == [4.33, None]
    assert transport.query["api_key"] == ["secret"]
    assert transport.query["file_type"] == ["json"]
    assert transport.query["series_id"] == ["FEDFUNDS"]
    assert transport.query["observation_start"] == ["2026-05-01"]
    assert transport.query["observation_end"] == ["2026-05-31"]
    assert transport.calls[0][1] == 2.5


def test_fred_provider_uses_fred_units_for_transformed_existing_indicators() -> None:
    transport = FakeHttpGet({"observations": [{"date": "2026-05-01", "value": "2.8"}]})
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=transport,
    )

    series = provider.get_series("cpi_yoy")

    assert series.indicator.indicator_id == "cpi_yoy"
    assert series.indicator.name == "Consumer Price Index Year-over-Year"
    assert transport.query["series_id"] == ["CPIAUCSL"]
    assert transport.query["units"] == ["pc1"]


def test_fred_provider_returns_latest_observation() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet(
            {
                "observations": [
                    {"date": "2026-03-01", "value": "4.20"},
                    {"date": "2026-04-01", "value": "4.10"},
                ]
            }
        ),
    )

    latest = provider.get_latest("fed_funds_rate")

    assert isinstance(latest, MacroObservation)
    assert latest.period == date(2026, 4, 1)
    assert latest.value == 4.10


def test_fred_provider_returns_snapshot_for_requested_indicators() -> None:
    transport = FakeHttpGet({"observations": [{"date": "2026-04-01", "value": "4.10"}]})
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=transport,
    )

    snapshot = provider.get_snapshot(
        ["fed_funds_rate", "unknown_series"],
        as_of_date=date(2026, 4, 30),
    )

    assert snapshot.as_of_date == date(2026, 4, 30)
    assert [series.indicator.indicator_id for series in snapshot.series] == [
        "fed_funds_rate",
        "unknown_series",
    ]
    assert len(transport.calls) == 1
    assert transport.query["observation_end"] == ["2026-04-30"]


def test_fred_provider_handles_unknown_series_without_network_call() -> None:
    transport = FakeHttpGet({"observations": []})
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=transport,
    )

    series = provider.get_series("not_a_known_indicator")
    latest = provider.get_latest("not_a_known_indicator")

    assert series.indicator.indicator_id == "not_a_known_indicator"
    assert series.indicator.category is MacroCategory.OTHER
    assert series.observations == []
    assert latest is None
    assert transport.calls == []


def test_fred_provider_returns_empty_series_for_empty_observations() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet({"observations": []}),
    )

    series = provider.get_series("DGS10")

    assert series.indicator.indicator_id == "treasury_10y_yield"
    assert series.observations == []


def test_fred_provider_requires_api_key_from_environment() -> None:
    provider = FREDMacroProvider(
        environ={},
        api_key_env_var="MISSING_FRED_KEY",
        http_get=FakeHttpGet({"observations": []}),
    )

    with pytest.raises(MacroDataConfigurationError, match="MISSING_FRED_KEY"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_maps_http_error_to_macro_error() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet(
            HTTPError("https://example.test", 404, "Not Found", hdrs=None, fp=None)
        ),
    )

    with pytest.raises(MacroDataHttpError, match="status 404"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_maps_timeout_to_macro_error() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet(URLError(TimeoutError("timed out"))),
    )

    with pytest.raises(MacroDataHttpError, match="HTTP request failed"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_maps_api_error_payload_to_macro_error() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet({"error_message": "Bad Request. Unknown series."}),
    )

    with pytest.raises(MacroDataHttpError, match="Unknown series"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_maps_malformed_json_to_macro_error() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet(b"not json"),
    )

    with pytest.raises(MacroDataParsingError, match="malformed JSON"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_rejects_malformed_observation_payload() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet({"observations": [{"date": "bad-date", "value": "4.1"}]}),
    )

    with pytest.raises(MacroDataParsingError, match="invalid date"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_rejects_malformed_observation_value() -> None:
    provider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet({"observations": [{"date": "2026-05-01", "value": []}]}),
    )

    with pytest.raises(MacroDataParsingError, match="invalid value"):
        provider.get_series("fed_funds_rate")


def test_fred_provider_satisfies_macro_provider_contract() -> None:
    provider: MacroDataProvider = FREDMacroProvider(
        environ={"FRED_API_KEY": "secret"},
        http_get=FakeHttpGet({"observations": []}),
    )

    assert isinstance(provider, MacroDataProvider)
