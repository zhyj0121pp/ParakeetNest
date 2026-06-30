"""Tests for the Macro Data Provider abstraction."""

from __future__ import annotations

import inspect
import sys
from datetime import date

import pytest

from parakeetnest.macro import (
    MacroCategory,
    MacroDataProvider,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)


class FakeMacroDataProvider(MacroDataProvider):
    """In-memory provider used to verify the abstract contract."""

    def __init__(self) -> None:
        self.indicator = MacroIndicator(
            indicator_id="growth_index",
            name="Growth Index",
            category=MacroCategory.GROWTH,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.INDEX,
            region="US",
        )
        self.observations = [
            MacroObservation(period=date(2026, 4, 30), value=101.2),
            MacroObservation(period=date(2026, 5, 31), value=101.8),
            MacroObservation(period=date(2026, 6, 30), value=102.1),
        ]

    def get_series(
        self,
        indicator_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MacroSeries:
        """Return deterministic series data without external dependencies."""
        if indicator_id != self.indicator.indicator_id:
            return MacroSeries(indicator=self._missing_indicator(indicator_id))

        observations = [
            observation
            for observation in self.observations
            if (start_date is None or observation.period >= start_date)
            and (end_date is None or observation.period <= end_date)
        ]
        return MacroSeries(indicator=self.indicator, observations=observations)

    def get_latest(self, indicator_id: str) -> MacroObservation | None:
        """Return the latest observation for known indicators."""
        series = self.get_series(indicator_id)
        if not series.observations:
            return None
        return series.observations[-1]

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Return deterministic snapshot data without external dependencies."""
        snapshot_date = as_of_date or date(2026, 6, 30)
        return MacroSnapshot(
            as_of_date=snapshot_date,
            series=[
                self.get_series(
                    indicator_id,
                    end_date=snapshot_date,
                )
                for indicator_id in indicator_ids
            ],
        )

    def _missing_indicator(self, indicator_id: str) -> MacroIndicator:
        return MacroIndicator(
            indicator_id=indicator_id,
            name=indicator_id.replace("_", " ").title(),
            category=MacroCategory.OTHER,
            frequency=MacroFrequency.IRREGULAR,
            unit=MacroUnit.OTHER,
        )


def test_macro_data_provider_cannot_be_instantiated_directly() -> None:
    """The base provider is an abstract contract, not an implementation."""
    with pytest.raises(TypeError, match="abstract"):
        MacroDataProvider()


def test_concrete_fake_provider_can_implement_interface() -> None:
    """A complete concrete implementation should satisfy the abstraction."""
    provider = FakeMacroDataProvider()

    assert isinstance(provider, MacroDataProvider)


def test_get_series_returns_macro_series() -> None:
    """Provider APIs should return provider-neutral macro series objects."""
    provider: MacroDataProvider = FakeMacroDataProvider()

    series = provider.get_series(
        "growth_index",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 6, 30),
    )

    assert isinstance(series, MacroSeries)
    assert series.indicator.indicator_id == "growth_index"
    assert [observation.period for observation in series.observations] == [
        date(2026, 5, 31),
        date(2026, 6, 30),
    ]


def test_get_latest_returns_macro_observation_or_none() -> None:
    """Latest observation lookups should return an observation or no value."""
    provider: MacroDataProvider = FakeMacroDataProvider()

    latest = provider.get_latest("growth_index")
    missing = provider.get_latest("missing_indicator")

    assert isinstance(latest, MacroObservation)
    assert latest.period == date(2026, 6, 30)
    assert missing is None


def test_get_snapshot_returns_macro_snapshot() -> None:
    """Provider snapshots should use the MacroSnapshot domain model."""
    provider: MacroDataProvider = FakeMacroDataProvider()

    snapshot = provider.get_snapshot(
        ["growth_index", "missing_indicator"],
        as_of_date=date(2026, 5, 31),
    )

    assert isinstance(snapshot, MacroSnapshot)
    assert snapshot.as_of_date == date(2026, 5, 31)
    assert [series.indicator.indicator_id for series in snapshot.series] == [
        "growth_index",
        "missing_indicator",
    ]
    assert len(snapshot.series[0].observations) == 2
    assert snapshot.series[1].observations == []


def test_macro_provider_contract_has_requested_signatures() -> None:
    """The provider interface should expose only the stable macro contract."""
    get_series = inspect.signature(MacroDataProvider.get_series)
    get_latest = inspect.signature(MacroDataProvider.get_latest)
    get_snapshot = inspect.signature(MacroDataProvider.get_snapshot)

    assert list(get_series.parameters) == [
        "self",
        "indicator_id",
        "start_date",
        "end_date",
    ]
    assert get_series.parameters["start_date"].default is None
    assert get_series.parameters["end_date"].default is None
    assert get_series.return_annotation == "MacroSeries"

    assert list(get_latest.parameters) == ["self", "indicator_id"]
    assert get_latest.return_annotation == "MacroObservation | None"

    assert list(get_snapshot.parameters) == [
        "self",
        "indicator_ids",
        "as_of_date",
    ]
    assert get_snapshot.parameters["as_of_date"].default is None
    assert get_snapshot.return_annotation == "MacroSnapshot"


def test_macro_provider_has_no_provider_specific_coupling() -> None:
    """The abstraction should not import clients or name concrete sources."""
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
    source = inspect.getsource(sys.modules[MacroDataProvider.__module__]).lower()

    assert all(name not in source for name in forbidden_names)


def test_macro_provider_abstraction_does_not_require_external_clients() -> None:
    """Importing and using the abstraction should avoid external data clients."""
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = FakeMacroDataProvider()

    assert isinstance(provider.get_series("growth_index"), MacroSeries)
    assert forbidden_modules.isdisjoint(sys.modules)
