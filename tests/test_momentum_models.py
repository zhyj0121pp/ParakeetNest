"""Tests for Momentum Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from parakeetnest.intelligence.momentum import (
    MomentumRegime,
    MomentumSnapshot,
    ReversalRisk,
)


AS_OF_DATE = date(2026, 6, 30)


def test_momentum_regime_values_are_stable() -> None:
    """Regimes should describe momentum conditions, not providers."""
    assert MomentumRegime.STRONG_UPTREND.value == "strong_uptrend"
    assert MomentumRegime.UPTREND.value == "uptrend"
    assert MomentumRegime.NEUTRAL.value == "neutral"
    assert MomentumRegime.DOWNTREND.value == "downtrend"
    assert MomentumRegime.STRONG_DOWNTREND.value == "strong_downtrend"


def test_reversal_risk_values_are_stable() -> None:
    """Reversal risk should expose stable severity levels."""
    assert ReversalRisk.LOW.value == "low"
    assert ReversalRisk.MEDIUM.value == "medium"
    assert ReversalRisk.HIGH.value == "high"


def test_momentum_snapshot_normalizes_fields_and_is_immutable() -> None:
    """Snapshots should capture point-in-time momentum evidence."""
    snapshot = MomentumSnapshot(
        symbol=" aapl ",
        as_of=AS_OF_DATE,
        price_change_1m=0.04,
        price_change_3m=0.11,
        price_change_6m=0.22,
        relative_strength=86,
        trend_strength=0.74,
        momentum_score=0.81,
        momentum_regime="strong_uptrend",
        reversal_risk="medium",
        confidence=0.78,
        evidence=(" 3m return leads benchmark ", ""),
    )

    assert snapshot.symbol == "AAPL"
    assert snapshot.as_of == AS_OF_DATE
    assert snapshot.price_change_1m == 0.04
    assert snapshot.price_change_3m == 0.11
    assert snapshot.price_change_6m == 0.22
    assert snapshot.relative_strength == 86.0
    assert snapshot.trend_strength == 0.74
    assert snapshot.momentum_score == 0.81
    assert snapshot.momentum_regime is MomentumRegime.STRONG_UPTREND
    assert snapshot.reversal_risk is ReversalRisk.MEDIUM
    assert snapshot.confidence == 0.78
    assert snapshot.evidence == ("3m return leads benchmark",)

    with pytest.raises(FrozenInstanceError):
        snapshot.momentum_score = 0.3


def test_momentum_models_have_no_provider_specific_fields() -> None:
    """Momentum models should avoid vendor-specific structure."""
    forbidden_names = {
        "yahoo",
        "ticker",
        "api",
        "database",
        "llm",
        "recommendation",
        "action",
        "trading",
    }

    field_names = {field.name.lower() for field in fields(MomentumSnapshot)}

    assert field_names.isdisjoint(forbidden_names)


def test_public_models_are_exported_from_momentum_package() -> None:
    """The package should expose the public momentum model surface."""
    import parakeetnest.intelligence.momentum as momentum

    assert momentum.MomentumRegime is MomentumRegime
    assert momentum.ReversalRisk is ReversalRisk
    assert momentum.MomentumSnapshot is MomentumSnapshot


def test_invalid_momentum_values_are_rejected() -> None:
    """Unknown enum strings should fail at the domain boundary."""
    with pytest.raises(ValueError):
        MomentumSnapshot(
            symbol="AAPL",
            as_of=AS_OF_DATE,
            price_change_1m=0.04,
            price_change_3m=0.11,
            price_change_6m=0.22,
            relative_strength=86,
            trend_strength=0.74,
            momentum_score=0.81,
            momentum_regime="breakout",
            reversal_risk=ReversalRisk.LOW,
            confidence=0.78,
        )

    with pytest.raises(ValueError):
        MomentumSnapshot(
            symbol="AAPL",
            as_of=AS_OF_DATE,
            price_change_1m=0.04,
            price_change_3m=0.11,
            price_change_6m=0.22,
            relative_strength=86,
            trend_strength=0.74,
            momentum_score=0.81,
            momentum_regime=MomentumRegime.UPTREND,
            reversal_risk="extreme",
            confidence=0.78,
        )
