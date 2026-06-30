"""Tests for Economic Regime domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from parakeetnest.regime import (
    EconomicRegime,
    EconomicRegimeClassifier,
    EconomicRegimeSnapshot,
    RegimeConfidence,
    RegimeIndicator,
    RegimeSignal,
)


def test_economic_regime_values_are_provider_agnostic() -> None:
    """Regimes should describe economic states, not data providers."""
    assert EconomicRegime.EXPANSION.value == "expansion"
    assert EconomicRegime.SLOWDOWN.value == "slowdown"
    assert EconomicRegime.RECESSION.value == "recession"
    assert EconomicRegime.RECOVERY.value == "recovery"
    assert EconomicRegime.STAGFLATION.value == "stagflation"
    assert (
        EconomicRegime.DISINFLATIONARY_GROWTH.value
        == "disinflationary_growth"
    )
    assert EconomicRegime.OVERHEATING.value == "overheating"
    assert EconomicRegime.UNKNOWN.value == "unknown"


def test_regime_signal_values_are_provider_neutral() -> None:
    """Signals should expose stable economic evidence families."""
    assert RegimeSignal.GROWTH.value == "growth"
    assert RegimeSignal.INFLATION.value == "inflation"
    assert RegimeSignal.LABOR.value == "labor"
    assert RegimeSignal.RATES.value == "rates"
    assert RegimeSignal.CREDIT.value == "credit"
    assert RegimeSignal.LIQUIDITY.value == "liquidity"
    assert RegimeSignal.CONSUMER.value == "consumer"
    assert RegimeSignal.FISCAL.value == "fiscal"
    assert RegimeSignal.SENTIMENT.value == "sentiment"
    assert RegimeSignal.OTHER.value == "other"


def test_regime_confidence_values_are_stable() -> None:
    """Confidence should be encoded independently from any provider score."""
    assert RegimeConfidence.LOW.value == "low"
    assert RegimeConfidence.MEDIUM.value == "medium"
    assert RegimeConfidence.HIGH.value == "high"
    assert RegimeConfidence.UNKNOWN.value == "unknown"


def test_regime_indicator_creation_normalizes_fields_and_is_immutable() -> None:
    """Indicators should carry normalized provider-neutral evidence."""
    indicator = RegimeIndicator(
        signal="inflation",
        name=" Core CPI Trend ",
        value=3.2,
        unit=" percent ",
        as_of_date=date(2026, 6, 30),
        interpretation=" inflation pressure is easing ",
    )

    assert indicator.signal is RegimeSignal.INFLATION
    assert indicator.name == "Core CPI Trend"
    assert indicator.value == 3.2
    assert indicator.unit == "percent"
    assert indicator.as_of_date == date(2026, 6, 30)
    assert indicator.interpretation == "inflation pressure is easing"

    with pytest.raises(FrozenInstanceError):
        indicator.name = "Headline CPI"


def test_regime_indicator_defaults_are_empty_provider_neutral_metadata() -> None:
    """Optional indicator metadata should default to empty neutral values."""
    indicator = RegimeIndicator(
        signal=RegimeSignal.GROWTH,
        name="Real GDP",
    )

    assert indicator.value is None
    assert indicator.unit is None
    assert indicator.as_of_date is None
    assert indicator.interpretation is None


def test_economic_regime_snapshot_construction_normalizes_metadata() -> None:
    """Snapshots should capture the regime view and supporting evidence."""
    labor = RegimeIndicator(
        signal=RegimeSignal.LABOR,
        name="Unemployment Rate",
        value=4.1,
        unit="percent",
    )
    growth = RegimeIndicator(
        signal=RegimeSignal.GROWTH,
        name="Real GDP Growth",
        value=2.0,
        unit="percent",
    )

    snapshot = EconomicRegimeSnapshot(
        regime="expansion",
        confidence="medium",
        indicators=[labor, growth],
        summary=" growth remains positive with labor cooling ",
        as_of_date=date(2026, 6, 30),
        source=" macro dashboard ",
    )

    assert snapshot.regime is EconomicRegime.EXPANSION
    assert snapshot.confidence is RegimeConfidence.MEDIUM
    assert [indicator.name for indicator in snapshot.indicators] == [
        "Real GDP Growth",
        "Unemployment Rate",
    ]
    assert snapshot.summary == "growth remains positive with labor cooling"
    assert snapshot.as_of_date == date(2026, 6, 30)
    assert snapshot.source == "macro dashboard"


def test_economic_regime_snapshot_defaults_are_provider_neutral() -> None:
    """Optional snapshot metadata should default to neutral empty values."""
    snapshot = EconomicRegimeSnapshot(
        regime=EconomicRegime.UNKNOWN,
        confidence=RegimeConfidence.UNKNOWN,
        as_of_date=date(2026, 6, 30),
    )

    assert snapshot.indicators == []
    assert snapshot.summary is None
    assert snapshot.source is None


def test_regime_models_have_no_provider_specific_fields() -> None:
    """Regime models should remain independent of provider implementations."""
    forbidden_names = {
        "fred",
        "yahoo",
        "sec",
        "macro_provider",
        "provider",
        "database",
        "llm",
    }

    for model in (RegimeIndicator, EconomicRegimeSnapshot):
        field_names = {field.name.lower() for field in fields(model)}
        assert field_names.isdisjoint(forbidden_names)


def test_public_models_are_exported_from_regime_package() -> None:
    """The package should expose the public regime domain surface."""
    import parakeetnest.regime as regime

    assert regime.EconomicRegime is EconomicRegime
    assert regime.RegimeSignal is RegimeSignal
    assert regime.RegimeConfidence is RegimeConfidence
    assert regime.RegimeIndicator is RegimeIndicator
    assert regime.EconomicRegimeSnapshot is EconomicRegimeSnapshot
    assert regime.EconomicRegimeClassifier is EconomicRegimeClassifier
    assert set(regime.__all__) == {
        "EconomicRegimeClassifier",
        "EconomicRegime",
        "EconomicRegimeSnapshot",
        "RegimeConfidence",
        "RegimeIndicator",
        "RegimeSignal",
    }


def test_invalid_regime_enum_values_are_rejected() -> None:
    """Unknown regime values should fail at the domain boundary."""
    with pytest.raises(ValueError):
        RegimeIndicator(
            signal="provider_signal",
            name="Example",
        )

    with pytest.raises(ValueError):
        EconomicRegimeSnapshot(
            regime="provider_regime",
            confidence=RegimeConfidence.UNKNOWN,
            as_of_date=date(2026, 6, 30),
        )

    with pytest.raises(ValueError):
        EconomicRegimeSnapshot(
            regime=EconomicRegime.UNKNOWN,
            confidence="certain",
            as_of_date=date(2026, 6, 30),
        )
