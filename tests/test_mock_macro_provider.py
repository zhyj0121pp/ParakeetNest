"""Tests for the deterministic mock macro data provider."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.macro import (
    MacroCategory,
    MacroDataProvider,
    MacroFrequency,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
    MockMacroDataProvider,
)


def test_mock_macro_provider_can_be_instantiated() -> None:
    """The mock provider should satisfy the macro provider contract."""
    provider = MockMacroDataProvider()

    assert isinstance(provider, MacroDataProvider)


def test_mock_macro_provider_returns_known_indicator_series() -> None:
    """Known macro indicators should return deterministic domain models."""
    provider = MockMacroDataProvider()

    series = provider.get_series("fed_funds_rate")

    assert isinstance(series, MacroSeries)
    assert series.indicator.indicator_id == "fed_funds_rate"
    assert series.indicator.category is MacroCategory.RATES
    assert series.indicator.unit is MacroUnit.PERCENT
    assert [observation.period for observation in series.observations] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
        date(2026, 6, 30),
    ]
    assert [observation.value for observation in series.observations] == [
        4.50,
        4.50,
        4.25,
        4.25,
        4.00,
        4.00,
    ]


def test_mock_macro_provider_exposes_core_built_in_indicators() -> None:
    """The local fixture set should cover the key research indicators."""
    provider = MockMacroDataProvider()
    indicator_ids = [
        "fed_funds_rate",
        "treasury_10y_yield",
        "cpi_yoy",
        "core_cpi_yoy",
        "unemployment_rate",
        "nonfarm_payrolls",
        "gdp_growth",
        "m2_growth",
    ]

    snapshot = provider.get_snapshot(indicator_ids)

    assert [series.indicator.indicator_id for series in snapshot.series] == sorted(
        indicator_ids,
    )
    assert all(series.observations for series in snapshot.series)


def test_mock_macro_provider_filters_series_by_date() -> None:
    """Date filters should be inclusive and deterministic."""
    provider = MockMacroDataProvider()

    series = provider.get_series(
        "cpi_yoy",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 5, 31),
    )

    assert [observation.period for observation in series.observations] == [
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ]
    assert [observation.value for observation in series.observations] == [
        3.00,
        2.90,
        2.80,
    ]


def test_mock_macro_provider_returns_latest_observation() -> None:
    """Latest lookups should return the final fixture observation."""
    provider = MockMacroDataProvider()

    latest = provider.get_latest("gdp_growth")

    assert isinstance(latest, MacroObservation)
    assert latest.period == date(2026, 6, 30)
    assert latest.value == 1.90


def test_mock_macro_provider_generates_snapshot_as_of_date() -> None:
    """Snapshots should cap each series at the requested date."""
    provider = MockMacroDataProvider()

    snapshot = provider.get_snapshot(
        ["fed_funds_rate", "cpi_yoy", "gdp_growth"],
        as_of_date=date(2026, 3, 31),
    )

    assert isinstance(snapshot, MacroSnapshot)
    assert snapshot.as_of_date == date(2026, 3, 31)
    assert [series.indicator.indicator_id for series in snapshot.series] == [
        "cpi_yoy",
        "fed_funds_rate",
        "gdp_growth",
    ]
    assert {
        series.indicator.indicator_id: series.observations[-1].period
        for series in snapshot.series
    } == {
        "cpi_yoy": date(2026, 3, 31),
        "fed_funds_rate": date(2026, 3, 31),
        "gdp_growth": date(2026, 3, 31),
    }


def test_mock_macro_provider_handles_unknown_indicator_safely() -> None:
    """Unknown indicators should return an empty neutral series."""
    provider = MockMacroDataProvider()

    series = provider.get_series("unknown_macro_indicator")
    latest = provider.get_latest("unknown_macro_indicator")

    assert series.indicator.indicator_id == "unknown_macro_indicator"
    assert series.indicator.category is MacroCategory.OTHER
    assert series.indicator.frequency is MacroFrequency.IRREGULAR
    assert series.indicator.unit is MacroUnit.OTHER
    assert series.observations == []
    assert latest is None


def test_mock_macro_provider_is_network_free_and_provider_neutral() -> None:
    """Using the mock should not import external clients or source adapters."""
    forbidden_names = {
        "fred",
        "yahoo",
        "bea",
        "bls",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "llm",
    }
    forbidden_modules = {
        "requests",
        "httpx",
        "yfinance",
        "aiohttp",
        "sqlite3",
    }
    source = inspect.getsource(sys.modules[MockMacroDataProvider.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = MockMacroDataProvider()
    series = provider.get_series("m2_growth")
    snapshot = provider.get_snapshot(["m2_growth", "missing"])

    assert isinstance(series, MacroSeries)
    assert isinstance(snapshot, MacroSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)
