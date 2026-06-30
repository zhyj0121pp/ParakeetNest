"""Tests for the deterministic Economic Regime classifier."""

from __future__ import annotations

from datetime import date

from parakeetnest.regime import (
    EconomicRegime,
    EconomicRegimeClassifier,
    EconomicRegimeSnapshot,
    RegimeConfidence,
)


AS_OF_DATE = date(2026, 6, 30)


def test_classifier_identifies_expansion() -> None:
    """Positive growth, moderate inflation, and low unemployment are expansion."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=2.6,
        inflation_rate=2.8,
        unemployment_rate=4.2,
        yield_curve_spread=0.8,
        policy_rate=3.5,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.EXPANSION
    assert snapshot.confidence is RegimeConfidence.HIGH
    assert snapshot.as_of_date == AS_OF_DATE
    assert snapshot.source == "rule_based_economic_regime_classifier"


def test_classifier_identifies_slowdown() -> None:
    """Subdued growth plus cooling evidence is slowdown."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=0.9,
        inflation_rate=3.2,
        unemployment_rate=4.4,
        yield_curve_spread=-0.2,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.SLOWDOWN
    assert snapshot.confidence is RegimeConfidence.MEDIUM


def test_classifier_identifies_recession() -> None:
    """Negative growth and elevated unemployment are recession."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=-1.2,
        inflation_rate=2.4,
        unemployment_rate=6.1,
        credit_spread=4.0,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.RECESSION


def test_classifier_identifies_recovery() -> None:
    """Positive growth with still-elevated unemployment is recovery."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=1.8,
        inflation_rate=2.7,
        unemployment_rate=5.8,
        yield_curve_spread=1.1,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.RECOVERY


def test_classifier_identifies_stagflation() -> None:
    """Weak growth, high inflation, and labor stress are stagflation."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=0.2,
        inflation_rate=5.5,
        unemployment_rate=5.7,
        policy_rate=5.25,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.STAGFLATION


def test_classifier_identifies_disinflationary_growth() -> None:
    """Positive growth with contained inflation is disinflationary growth."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=2.2,
        inflation_rate=2.1,
        unemployment_rate=4.6,
        yield_curve_spread=0.6,
        credit_spread=1.4,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.DISINFLATIONARY_GROWTH
    assert snapshot.confidence is RegimeConfidence.HIGH


def test_classifier_identifies_overheating() -> None:
    """Strong growth, high inflation, and tight labor are overheating."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=3.8,
        inflation_rate=4.6,
        unemployment_rate=3.6,
        policy_rate=4.8,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.OVERHEATING


def test_classifier_returns_unknown_for_missing_core_data() -> None:
    """Missing core macro evidence should not crash or force a regime."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=2.1,
        yield_curve_spread=0.4,
        as_of_date=AS_OF_DATE,
    )

    assert isinstance(snapshot, EconomicRegimeSnapshot)
    assert snapshot.regime is EconomicRegime.UNKNOWN
    assert snapshot.confidence is RegimeConfidence.UNKNOWN
    assert [indicator.name for indicator in snapshot.indicators] == [
        "Real GDP Growth",
        "Yield Curve Spread",
    ]


def test_classifier_ignores_invalid_values() -> None:
    """Invalid values should be ignored and never appear as evidence."""
    snapshot = EconomicRegimeClassifier().classify(
        real_gdp_growth=float("nan"),
        inflation_rate="2.2",
        unemployment_rate=-1.0,
        yield_curve_spread=True,
        policy_rate=float("inf"),
        credit_spread=1.2,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.regime is EconomicRegime.UNKNOWN
    assert snapshot.confidence is RegimeConfidence.UNKNOWN
    assert [indicator.name for indicator in snapshot.indicators] == [
        "Credit Spread",
    ]
