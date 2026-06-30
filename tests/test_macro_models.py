"""Tests for Macro Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, date, datetime

import pytest

from parakeetnest.macro import (
    MacroCategory,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)


def test_macro_category_values_are_provider_agnostic() -> None:
    """Macro categories should describe the economy, not data providers."""
    assert MacroCategory.GROWTH.value == "growth"
    assert MacroCategory.INFLATION.value == "inflation"
    assert MacroCategory.LABOR.value == "labor"
    assert MacroCategory.RATES.value == "rates"
    assert MacroCategory.CREDIT.value == "credit"
    assert MacroCategory.HOUSING.value == "housing"
    assert MacroCategory.CONSUMER.value == "consumer"
    assert MacroCategory.TRADE.value == "trade"
    assert MacroCategory.FISCAL.value == "fiscal"
    assert MacroCategory.MONEY.value == "money"
    assert MacroCategory.SENTIMENT.value == "sentiment"
    assert MacroCategory.OTHER.value == "other"


def test_macro_frequency_values_are_provider_neutral() -> None:
    """Frequencies should expose stable strings independent of provider cadence."""
    assert MacroFrequency.DAILY.value == "daily"
    assert MacroFrequency.WEEKLY.value == "weekly"
    assert MacroFrequency.MONTHLY.value == "monthly"
    assert MacroFrequency.QUARTERLY.value == "quarterly"
    assert MacroFrequency.ANNUAL.value == "annual"
    assert MacroFrequency.IRREGULAR.value == "irregular"


def test_macro_unit_values_are_provider_neutral() -> None:
    """Units should use common economic meanings rather than provider labels."""
    assert MacroUnit.INDEX.value == "index"
    assert MacroUnit.PERCENT.value == "percent"
    assert MacroUnit.PERCENTAGE_POINT.value == "percentage_point"
    assert MacroUnit.BASIS_POINT.value == "basis_point"
    assert MacroUnit.CURRENCY.value == "currency"
    assert MacroUnit.CURRENCY_PER_UNIT.value == "currency_per_unit"
    assert MacroUnit.PERSONS.value == "persons"
    assert MacroUnit.COUNT.value == "count"
    assert MacroUnit.THOUSANDS.value == "thousands"
    assert MacroUnit.MILLIONS.value == "millions"
    assert MacroUnit.BILLIONS.value == "billions"
    assert MacroUnit.RATIO.value == "ratio"
    assert MacroUnit.OTHER.value == "other"


def test_macro_indicator_creation_normalizes_fields_and_is_immutable() -> None:
    """Indicators should carry normalized provider-neutral metadata."""
    indicator = MacroIndicator(
        indicator_id=" Real_GDP ",
        name=" Real Gross Domestic Product ",
        category="growth",
        frequency="quarterly",
        unit="billions",
        region=" us ",
        description=" Inflation-adjusted economic output ",
    )

    assert indicator.indicator_id == "real_gdp"
    assert indicator.name == "Real Gross Domestic Product"
    assert indicator.category is MacroCategory.GROWTH
    assert indicator.frequency is MacroFrequency.QUARTERLY
    assert indicator.unit is MacroUnit.BILLIONS
    assert indicator.region == "US"
    assert indicator.description == "Inflation-adjusted economic output"

    with pytest.raises(FrozenInstanceError):
        indicator.name = "Nominal GDP"


def test_macro_observation_creation() -> None:
    """Observations should capture period value and release metadata."""
    released_at = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
    revised_at = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)
    observation = MacroObservation(
        period=date(2026, 3, 31),
        value=7_125.4,
        released_at=released_at,
        revised_at=revised_at,
    )

    assert observation.period == date(2026, 3, 31)
    assert observation.value == 7_125.4
    assert observation.released_at == released_at
    assert observation.revised_at == revised_at


def test_macro_series_orders_observations_chronologically() -> None:
    """Series should be stable for consumers regardless of provider ordering."""
    indicator = MacroIndicator(
        indicator_id="unemployment_rate",
        name="Unemployment Rate",
        category=MacroCategory.LABOR,
        frequency=MacroFrequency.MONTHLY,
        unit=MacroUnit.PERCENT,
        region="US",
    )
    series = MacroSeries(
        indicator=indicator,
        observations=[
            MacroObservation(period=date(2026, 3, 31), value=4.1),
            MacroObservation(period=date(2026, 1, 31), value=4.0),
            MacroObservation(period=date(2026, 2, 28), value=4.2),
        ],
    )

    assert series.indicator == indicator
    assert [observation.period for observation in series.observations] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]


def test_macro_snapshot_groups_series_and_cleans_notes() -> None:
    """Snapshots should hold a point-in-time set of macro series."""
    inflation = MacroIndicator(
        indicator_id="inflation_rate",
        name="Inflation Rate",
        category=MacroCategory.INFLATION,
        frequency=MacroFrequency.MONTHLY,
        unit=MacroUnit.PERCENT,
    )
    policy_rate = MacroIndicator(
        indicator_id="policy_rate",
        name="Policy Rate",
        category=MacroCategory.RATES,
        frequency=MacroFrequency.DAILY,
        unit=MacroUnit.PERCENT,
    )
    snapshot = MacroSnapshot(
        as_of_date=date(2026, 6, 30),
        series=[
            MacroSeries(indicator=policy_rate),
            MacroSeries(indicator=inflation),
        ],
        notes=[" latest available values ", ""],
    )

    assert snapshot.as_of_date == date(2026, 6, 30)
    assert [item.indicator.indicator_id for item in snapshot.series] == [
        "inflation_rate",
        "policy_rate",
    ]
    assert snapshot.notes == ["latest available values"]


def test_macro_models_have_no_provider_specific_fields() -> None:
    """Domain models should remain independent of provider implementations."""
    forbidden_names = {
        "fred",
        "yahoo",
        "bea",
        "bls",
        "provider",
        "database",
        "llm",
    }

    for model in (MacroIndicator, MacroObservation, MacroSeries, MacroSnapshot):
        field_names = {field.name.lower() for field in fields(model)}
        assert field_names.isdisjoint(forbidden_names)


def test_invalid_macro_enum_values_are_rejected() -> None:
    """Unknown macro metadata should fail at the domain boundary."""
    with pytest.raises(ValueError):
        MacroIndicator(
            indicator_id="x",
            name="Example",
            category="provider_growth",
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.INDEX,
        )

    with pytest.raises(ValueError):
        MacroIndicator(
            indicator_id="x",
            name="Example",
            category=MacroCategory.GROWTH,
            frequency="provider_monthly",
            unit=MacroUnit.INDEX,
        )

    with pytest.raises(ValueError):
        MacroIndicator(
            indicator_id="x",
            name="Example",
            category=MacroCategory.GROWTH,
            frequency=MacroFrequency.MONTHLY,
            unit="provider_unit",
        )
