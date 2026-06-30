"""Tests for Market Breadth domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from parakeetnest.intelligence.market_breadth import (
    BreadthRegime,
    MarketBreadthSnapshot,
)


AS_OF_DATE = date(2026, 6, 30)


def test_breadth_regime_values_are_stable() -> None:
    """Regimes should describe breadth conditions, not providers."""
    assert BreadthRegime.STRONG.value == "strong"
    assert BreadthRegime.HEALTHY.value == "healthy"
    assert BreadthRegime.NEUTRAL.value == "neutral"
    assert BreadthRegime.WEAK.value == "weak"
    assert BreadthRegime.STRESSED.value == "stressed"
    assert BreadthRegime.UNKNOWN.value == "unknown"


def test_market_breadth_snapshot_normalizes_fields_and_is_immutable() -> None:
    """Snapshots should capture point-in-time breadth evidence."""
    snapshot = MarketBreadthSnapshot(
        universe=" sp500 ",
        date=AS_OF_DATE,
        advancers=320,
        decliners=170,
        unchanged=10,
        new_highs=55,
        new_lows=12,
        percent_above_20d_ma=64,
        percent_above_50d_ma=61,
        percent_above_200d_ma=57,
        up_volume=4_500_000_000,
        down_volume=2_700_000_000,
        breadth_score=0.68,
        breadth_regime="healthy",
        warnings=(" new lows are still elevated ", ""),
    )

    assert snapshot.universe == "SP500"
    assert snapshot.date == AS_OF_DATE
    assert snapshot.advancers == 320
    assert snapshot.decliners == 170
    assert snapshot.unchanged == 10
    assert snapshot.new_highs == 55
    assert snapshot.new_lows == 12
    assert snapshot.percent_above_20d_ma == 64.0
    assert snapshot.percent_above_50d_ma == 61.0
    assert snapshot.percent_above_200d_ma == 57.0
    assert snapshot.up_volume == 4_500_000_000.0
    assert snapshot.down_volume == 2_700_000_000.0
    assert snapshot.breadth_score == 0.68
    assert snapshot.breadth_regime is BreadthRegime.HEALTHY
    assert snapshot.warnings == ("new lows are still elevated",)

    with pytest.raises(FrozenInstanceError):
        snapshot.breadth_score = 0.4


def test_market_breadth_models_have_no_provider_specific_fields() -> None:
    """Market breadth models should avoid vendor-specific structure."""
    forbidden_names = {
        "yahoo",
        "ticker",
        "symbol",
        "api",
        "database",
        "llm",
        "recommendation",
        "action",
        "trading",
    }

    field_names = {field.name.lower() for field in fields(MarketBreadthSnapshot)}

    assert field_names.isdisjoint(forbidden_names)


def test_public_models_are_exported_from_market_breadth_package() -> None:
    """The package should expose the public market breadth model surface."""
    import parakeetnest.intelligence.market_breadth as market_breadth

    assert market_breadth.BreadthRegime is BreadthRegime
    assert market_breadth.MarketBreadthSnapshot is MarketBreadthSnapshot


def test_invalid_breadth_regime_values_are_rejected() -> None:
    """Unknown regime strings should fail at the domain boundary."""
    with pytest.raises(ValueError):
        MarketBreadthSnapshot(
            universe="SP500",
            date=AS_OF_DATE,
            advancers=250,
            decliners=240,
            unchanged=10,
            new_highs=20,
            new_lows=20,
            percent_above_20d_ma=50,
            percent_above_50d_ma=50,
            percent_above_200d_ma=50,
            up_volume=3_000_000_000,
            down_volume=3_000_000_000,
            breadth_score=0.5,
            breadth_regime="expanding",
            warnings=(),
        )
