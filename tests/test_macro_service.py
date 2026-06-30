"""Tests for the provider-agnostic macro data service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.macro import (
    MacroCategory,
    MacroDataProvider,
    MacroDataService,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)


class SpyMacroDataProvider(MacroDataProvider):
    """Provider test double that records service delegation."""

    def __init__(self) -> None:
        self.series_calls: list[tuple[str, date | None, date | None]] = []
        self.latest_calls: list[str] = []
        self.snapshot_calls: list[tuple[list[str], date | None]] = []
        self.indicator = MacroIndicator(
            indicator_id="policy_rate",
            name="Policy Rate",
            category=MacroCategory.RATES,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
        )
        self.series = MacroSeries(
            indicator=self.indicator,
            observations=[
                MacroObservation(period=date(2026, 5, 31), value=4.25),
                MacroObservation(period=date(2026, 6, 30), value=4.00),
            ],
        )
        self.unknown_series = MacroSeries(
            indicator=MacroIndicator(
                indicator_id="missing_indicator",
                name="Missing Indicator",
                category=MacroCategory.OTHER,
                frequency=MacroFrequency.IRREGULAR,
                unit=MacroUnit.OTHER,
            )
        )
        self.snapshot = MacroSnapshot(
            as_of_date=date(2026, 6, 30),
            series=[self.series, self.unknown_series],
        )

    def get_series(
        self,
        indicator_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MacroSeries:
        """Record series delegation and return prepared data."""
        self.series_calls.append((indicator_id, start_date, end_date))
        if indicator_id == self.indicator.indicator_id:
            return self.series
        return self.unknown_series

    def get_latest(self, indicator_id: str) -> MacroObservation | None:
        """Record latest delegation and return prepared data."""
        self.latest_calls.append(indicator_id)
        if indicator_id == self.indicator.indicator_id:
            return self.series.observations[-1]
        return None

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Record snapshot delegation and return prepared data."""
        self.snapshot_calls.append((indicator_ids, as_of_date))
        return self.snapshot


def test_get_series_delegates_to_provider() -> None:
    """The service should return exactly what the provider returns."""
    provider = SpyMacroDataProvider()
    service = MacroDataService(provider)

    series = service.get_series(
        "policy_rate",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 6, 30),
    )

    assert series is provider.series
    assert isinstance(series, MacroSeries)
    assert provider.series_calls == [
        ("policy_rate", date(2026, 5, 1), date(2026, 6, 30))
    ]


def test_get_latest_delegates_to_provider() -> None:
    """Latest observation lookups should be delegated without service logic."""
    provider = SpyMacroDataProvider()
    service = MacroDataService(provider)

    latest = service.get_latest("policy_rate")

    assert latest is provider.series.observations[-1]
    assert isinstance(latest, MacroObservation)
    assert provider.latest_calls == ["policy_rate"]


def test_get_snapshot_delegates_to_provider() -> None:
    """Snapshot requests should be delegated with indicator IDs and date."""
    provider = SpyMacroDataProvider()
    service = MacroDataService(provider)
    indicator_ids = ["policy_rate", "missing_indicator"]

    snapshot = service.get_snapshot(indicator_ids, as_of_date=date(2026, 6, 30))

    assert snapshot is provider.snapshot
    assert isinstance(snapshot, MacroSnapshot)
    assert provider.snapshot_calls == [(indicator_ids, date(2026, 6, 30))]


def test_unknown_indicator_behavior_comes_from_provider() -> None:
    """Unknown indicators should not be interpreted by the service boundary."""
    provider = SpyMacroDataProvider()
    service = MacroDataService(provider)

    series = service.get_series("missing_indicator")
    latest = service.get_latest("missing_indicator")

    assert series is provider.unknown_series
    assert series.observations == []
    assert latest is None
    assert provider.series_calls == [("missing_indicator", None, None)]
    assert provider.latest_calls == ["missing_indicator"]


def test_macro_service_is_exported_from_package() -> None:
    """The macro package should expose the service boundary."""
    provider = SpyMacroDataProvider()

    assert MacroDataService(provider).__class__ is MacroDataService


def test_macro_service_is_network_free_and_provider_neutral() -> None:
    """The service boundary should not import external clients or adapters."""
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
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[MacroDataService.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: MacroDataProvider = SpyMacroDataProvider()
    service = MacroDataService(provider)

    assert isinstance(service.get_series("policy_rate"), MacroSeries)
    assert isinstance(service.get_snapshot(["policy_rate"]), MacroSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)
