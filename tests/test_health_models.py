"""Tests for Market Health Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from parakeetnest.intelligence.health import (
    HealthComponentState,
    MarketHealthComponent,
    MarketHealthSnapshot,
    MarketHealthState,
)


AS_OF_DATE = date(2026, 6, 30)


def test_market_health_state_values_are_stable() -> None:
    """Health enum values should remain stable for downstream consumers."""
    assert [state.value for state in MarketHealthState] == [
        "robust",
        "healthy",
        "fragile",
        "deteriorating",
        "stressed",
        "unknown",
    ]


def test_health_component_state_values_are_stable() -> None:
    """Component state enum values should remain stable."""
    assert [state.value for state in HealthComponentState] == [
        "positive",
        "neutral",
        "negative",
        "warning",
        "unknown",
    ]


def test_market_health_component_fields_are_provider_neutral() -> None:
    """Components should contain neutral facts and scoring fields only."""
    field_names = {field.name for field in fields(MarketHealthComponent)}

    assert field_names == {
        "name",
        "state",
        "score",
        "weight",
        "evidence",
        "metadata",
    }


def test_market_health_component_normalizes_values_and_is_immutable() -> None:
    """Component values should normalize without provider-specific payloads."""
    component = MarketHealthComponent(
        name=" Momentum ",
        state="positive",
        score="0.72",
        weight="0.20",
        evidence=[" constructive tape ", ""],
        metadata={"source": "fixture"},
    )

    assert component.name == "momentum"
    assert component.state is HealthComponentState.POSITIVE
    assert component.score == 0.72
    assert component.weight == 0.20
    assert component.evidence == ("constructive tape",)
    assert component.metadata["source"] == "fixture"

    with pytest.raises(FrozenInstanceError):
        component.score = 0.1


def test_market_health_snapshot_fields_are_provider_neutral() -> None:
    """Snapshots should not contain recommendation, vendor, or trading fields."""
    field_names = {field.name for field in fields(MarketHealthSnapshot)}

    assert field_names == {
        "as_of",
        "universe",
        "health_state",
        "health_score",
        "confidence",
        "components",
        "positives",
        "negatives",
        "warnings",
        "metadata",
    }


def test_market_health_snapshot_normalizes_values_and_is_immutable() -> None:
    """Snapshots should normalize score, confidence, enums, and collections."""
    component = MarketHealthComponent(
        name="breadth",
        state=HealthComponentState.POSITIVE,
        score=0.70,
    )
    snapshot = MarketHealthSnapshot(
        as_of=AS_OF_DATE,
        universe=" us ",
        health_state="healthy",
        health_score="0.68",
        confidence="0.83",
        components=[component],
        positives=[" breadth constructive "],
        negatives=[""],
        warnings=[" risk elevated "],
        metadata={"version": 1},
    )

    assert snapshot.universe == "US"
    assert snapshot.health_state is MarketHealthState.HEALTHY
    assert snapshot.health_score == 0.68
    assert snapshot.confidence == 0.83
    assert snapshot.components == (component,)
    assert snapshot.positives == ("breadth constructive",)
    assert snapshot.negatives == ()
    assert snapshot.warnings == ("risk elevated",)
    assert snapshot.metadata["version"] == 1

    with pytest.raises(FrozenInstanceError):
        snapshot.confidence = 0.1
