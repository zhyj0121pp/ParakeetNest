"""Tests for deterministic market health calculations."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from parakeetnest.intelligence.health import (
    HealthComponentState,
    MarketHealthCalculator,
    MarketHealthComponent,
    MarketHealthSnapshot,
    MarketHealthState,
)


AS_OF_DATE = date(2026, 6, 30)


def component(
    name: str,
    score: float,
    *,
    state: HealthComponentState = HealthComponentState.POSITIVE,
) -> MarketHealthComponent:
    """Build one market health component fixture."""
    return MarketHealthComponent(
        name=name,
        state=state,
        score=score,
        evidence=(f"{name} evidence",),
    )


def all_components(
    *,
    economic_regime: float = 0.72,
    risk: float = 0.40,
    breadth: float = 0.68,
    momentum: float = 0.74,
    sentiment: float = 0.58,
    sector_rotation: float = 0.55,
) -> tuple[MarketHealthComponent, ...]:
    """Build the full default component set."""
    return (
        component("economic_regime", economic_regime),
        component("risk", risk, state=HealthComponentState.WARNING),
        component("breadth", breadth),
        component("momentum", momentum),
        component("sentiment", sentiment, state=HealthComponentState.NEUTRAL),
        component("sector_rotation", sector_rotation, state=HealthComponentState.NEUTRAL),
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.80, MarketHealthState.ROBUST),
        (0.7999, MarketHealthState.HEALTHY),
        (0.65, MarketHealthState.HEALTHY),
        (0.6499, MarketHealthState.FRAGILE),
        (0.45, MarketHealthState.FRAGILE),
        (0.4499, MarketHealthState.DETERIORATING),
        (0.30, MarketHealthState.DETERIORATING),
        (0.2999, MarketHealthState.STRESSED),
        (-1.0, MarketHealthState.STRESSED),
        (2.0, MarketHealthState.ROBUST),
    ],
)
def test_classify_health_uses_documented_thresholds(
    score: float,
    expected: MarketHealthState,
) -> None:
    """Health thresholds should be inclusive at documented cutoffs."""
    assert MarketHealthCalculator.classify_health(score) is expected


def test_calculate_score_uses_default_weighted_normalization() -> None:
    """Scores should be weighted and normalized by available component weight."""
    calculator = MarketHealthCalculator()

    score = calculator.calculate_score(all_components())

    assert score == pytest.approx(
        (0.72 * 0.20)
        + (0.40 * 0.20)
        + (0.68 * 0.20)
        + (0.74 * 0.20)
        + (0.58 * 0.10)
        + (0.55 * 0.10)
    )


def test_partial_components_normalize_by_available_weight() -> None:
    """Partial data should still produce a proportional weighted score."""
    calculator = MarketHealthCalculator()
    components = (
        component("economic_regime", 0.90),
        component("risk", 0.30, state=HealthComponentState.WARNING),
    )

    score = calculator.calculate_score(calculator.normalize_components(components))

    assert score == pytest.approx(((0.90 * 0.20) + (0.30 * 0.20)) / 0.40)


def test_calculate_returns_unknown_when_no_components_are_available() -> None:
    """No usable data should produce UNKNOWN with zero score and confidence."""
    snapshot = MarketHealthCalculator().calculate(
        as_of=AS_OF_DATE,
        universe="US",
        components=(),
    )

    assert snapshot.health_state is MarketHealthState.UNKNOWN
    assert snapshot.health_score == 0.0
    assert snapshot.confidence == 0.0
    assert snapshot.components == ()
    assert snapshot.positives == ()
    assert snapshot.negatives == ()
    assert snapshot.warnings == ()


def test_calculate_returns_health_snapshot_with_sensible_summaries() -> None:
    """Composite snapshots should include populated component summaries."""
    snapshot = MarketHealthCalculator().calculate(
        as_of=AS_OF_DATE,
        universe="US",
        components=all_components(),
    )

    assert isinstance(snapshot, MarketHealthSnapshot)
    assert snapshot.health_score == pytest.approx(0.621)
    assert snapshot.health_state is MarketHealthState.FRAGILE
    assert snapshot.confidence == 1.0
    assert len(snapshot.components) == 6
    assert any("economic_regime" in item for item in snapshot.positives)
    assert any("risk" in item for item in snapshot.warnings)


def test_score_for_component_falls_back_to_component_state() -> None:
    """Components can be supplied as state-only inputs."""
    calculator = MarketHealthCalculator()
    components = calculator.normalize_components(
        (
            MarketHealthComponent("economic_regime", HealthComponentState.POSITIVE),
            MarketHealthComponent("risk", HealthComponentState.NEGATIVE),
            MarketHealthComponent("breadth", HealthComponentState.WARNING),
            MarketHealthComponent("momentum", HealthComponentState.NEUTRAL),
        )
    )

    assert tuple(component.score for component in components) == (
        0.85,
        0.15,
        0.35,
        0.55,
    )


def test_calculator_accepts_simplified_dependency_snapshots() -> None:
    """Dependency-like snapshots should convert without importing prior layers."""
    snapshot = MarketHealthCalculator().calculate(
        as_of=AS_OF_DATE,
        universe="US",
        economic_regime={"score": 0.80, "state": "positive"},
        risk={"overall_score": 35, "overall_level": "elevated"},
        breadth=SimpleNamespace(breadth_score=0.70, evidence=("Breadth broad.",)),
        momentum=SimpleNamespace(momentum_score=0.75, regime="strong_uptrend"),
        sentiment=SimpleNamespace(overall_score=62, regime="greed"),
        sector_rotation={"rotation_score": 0.52, "state": "neutral"},
    )

    assert snapshot.confidence == 1.0
    assert tuple(component.name for component in snapshot.components) == (
        "economic_regime",
        "sector_rotation",
        "risk",
        "breadth",
        "momentum",
        "sentiment",
    )
    assert any("risk" in item for item in snapshot.warnings)


def test_unknown_components_are_excluded_from_score_and_confidence() -> None:
    """Unknown component facts should not inflate score or availability."""
    calculator = MarketHealthCalculator()
    snapshot = calculator.calculate(
        as_of=AS_OF_DATE,
        universe="US",
        components=(
            MarketHealthComponent("economic_regime", HealthComponentState.UNKNOWN),
            component("momentum", 0.90),
        ),
    )

    assert snapshot.health_score == 0.90
    assert snapshot.confidence == 0.1667
