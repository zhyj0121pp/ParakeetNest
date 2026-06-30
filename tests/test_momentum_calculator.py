"""Tests for deterministic momentum calculations."""

from __future__ import annotations

import inspect
import sys
from datetime import date

import pytest

from parakeetnest.intelligence.momentum import (
    MomentumCalculator,
    MomentumInputs,
    MomentumRegime,
    MomentumSnapshot,
    ReversalRisk,
)


AS_OF_DATE = date(2026, 6, 30)


def momentum_inputs(
    *,
    price_change_1m: float = 0.04,
    price_change_3m: float = 0.10,
    price_change_6m: float = 0.20,
    relative_strength: float = 75,
    trend_strength: float = 0.70,
) -> MomentumInputs:
    return MomentumInputs(
        symbol="AAPL",
        as_of=AS_OF_DATE,
        price_change_1m=price_change_1m,
        price_change_3m=price_change_3m,
        price_change_6m=price_change_6m,
        relative_strength=relative_strength,
        trend_strength=trend_strength,
    )


def test_calculator_returns_strong_uptrend_snapshot() -> None:
    """Strong positive inputs should classify as a strong uptrend."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=0.08,
            price_change_3m=0.18,
            price_change_6m=0.32,
            relative_strength=90,
            trend_strength=0.86,
        )
    )

    assert isinstance(snapshot, MomentumSnapshot)
    assert snapshot.momentum_score >= 0.75
    assert snapshot.momentum_regime is MomentumRegime.STRONG_UPTREND


def test_calculator_returns_uptrend_snapshot() -> None:
    """Constructive but less extreme inputs should classify as an uptrend."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=0.02,
            price_change_3m=0.07,
            price_change_6m=0.12,
            relative_strength=62,
            trend_strength=0.58,
        )
    )

    assert snapshot.momentum_regime is MomentumRegime.UPTREND
    assert 0.58 <= snapshot.momentum_score < 0.75


def test_calculator_returns_neutral_snapshot() -> None:
    """Mixed or flat inputs should classify as neutral."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=0.00,
            price_change_3m=0.00,
            price_change_6m=0.00,
            relative_strength=50,
            trend_strength=0.50,
        )
    )

    assert snapshot.momentum_score == pytest.approx(0.50)
    assert snapshot.momentum_regime is MomentumRegime.NEUTRAL


def test_calculator_returns_downtrend_snapshot() -> None:
    """Weak inputs should classify as a downtrend."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=-0.08,
            price_change_3m=-0.14,
            price_change_6m=-0.18,
            relative_strength=34,
            trend_strength=0.34,
        )
    )

    assert snapshot.momentum_regime is MomentumRegime.DOWNTREND
    assert 0.25 <= snapshot.momentum_score < 0.42


def test_calculator_returns_strong_downtrend_snapshot() -> None:
    """Deeply negative inputs should classify as a strong downtrend."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=-0.16,
            price_change_3m=-0.24,
            price_change_6m=-0.34,
            relative_strength=12,
            trend_strength=0.12,
        )
    )

    assert snapshot.momentum_score < 0.25
    assert snapshot.momentum_regime is MomentumRegime.STRONG_DOWNTREND


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (-1.0, MomentumRegime.STRONG_DOWNTREND),
        (0.0, MomentumRegime.STRONG_DOWNTREND),
        (0.2499, MomentumRegime.STRONG_DOWNTREND),
        (0.25, MomentumRegime.DOWNTREND),
        (0.4199, MomentumRegime.DOWNTREND),
        (0.42, MomentumRegime.NEUTRAL),
        (0.5799, MomentumRegime.NEUTRAL),
        (0.58, MomentumRegime.UPTREND),
        (0.7499, MomentumRegime.UPTREND),
        (0.75, MomentumRegime.STRONG_UPTREND),
        (1.0, MomentumRegime.STRONG_UPTREND),
        (2.0, MomentumRegime.STRONG_UPTREND),
    ],
)
def test_classify_momentum_uses_stable_threshold_boundaries(
    score: float,
    expected: MomentumRegime,
) -> None:
    """Momentum regime thresholds should be inclusive at documented cutoffs."""
    assert MomentumCalculator.classify_momentum(score) is expected


def test_score_normalization_clamps_extreme_provider_inputs() -> None:
    """Out-of-range raw inputs should not push scores outside the public range."""
    calculator = MomentumCalculator()

    maximum = calculator.calculate_score(
        momentum_inputs(
            price_change_1m=10.0,
            price_change_3m=10.0,
            price_change_6m=10.0,
            relative_strength=250,
            trend_strength=3.0,
        )
    )
    minimum = calculator.calculate_score(
        momentum_inputs(
            price_change_1m=-10.0,
            price_change_3m=-10.0,
            price_change_6m=-10.0,
            relative_strength=-50,
            trend_strength=-2.0,
        )
    )

    assert maximum == 1.0
    assert minimum == 0.0


def test_calculator_identifies_high_reversal_risk() -> None:
    """Sharp short-term extension in an uptrend should flag high reversal risk."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=0.18,
            price_change_3m=0.20,
            price_change_6m=0.30,
            relative_strength=88,
            trend_strength=0.84,
        )
    )

    assert snapshot.reversal_risk is ReversalRisk.HIGH


def test_calculator_identifies_low_reversal_risk() -> None:
    """Orderly positive trends should carry low reversal risk."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=0.04,
            price_change_3m=0.12,
            price_change_6m=0.20,
            relative_strength=74,
            trend_strength=0.72,
        )
    )

    assert snapshot.reversal_risk is ReversalRisk.LOW


@pytest.mark.parametrize(
    (
        "price_change_1m",
        "price_change_3m",
        "price_change_6m",
        "expected",
    ),
    [
        (0.11, 0.09, 0.16, ReversalRisk.HIGH),
        (0.15, 0.01, 0.01, ReversalRisk.HIGH),
        (0.06, 0.12, 0.20, ReversalRisk.LOW),
        (0.04, 0.08, 0.12, ReversalRisk.LOW),
        (-0.09, -0.12, -0.18, ReversalRisk.MEDIUM),
    ],
)
def test_reversal_risk_boundary_cases_are_stable(
    price_change_1m: float,
    price_change_3m: float,
    price_change_6m: float,
    expected: ReversalRisk,
) -> None:
    """Reversal risk should keep exact high/low boundary behavior stable."""
    inputs = momentum_inputs(
        price_change_1m=price_change_1m,
        price_change_3m=price_change_3m,
        price_change_6m=price_change_6m,
    )

    assert MomentumCalculator.classify_reversal_risk(inputs) is expected


def test_calculator_confidence_is_normalized_and_higher_for_aligned_signals() -> None:
    """Confidence should stay in range and rise when signals agree."""
    calculator = MomentumCalculator()

    aligned = calculator.calculate(
        momentum_inputs(
            price_change_1m=0.08,
            price_change_3m=0.18,
            price_change_6m=0.32,
            relative_strength=90,
            trend_strength=0.86,
        )
    )
    mixed = calculator.calculate(
        momentum_inputs(
            price_change_1m=0.10,
            price_change_3m=-0.08,
            price_change_6m=0.02,
            relative_strength=45,
            trend_strength=0.40,
        )
    )

    assert 0.0 <= aligned.confidence <= 1.0
    assert 0.0 <= mixed.confidence <= 1.0
    assert aligned.confidence > mixed.confidence


@pytest.mark.parametrize(
    ("inputs", "momentum_score", "expected"),
    [
        (
            momentum_inputs(
                price_change_1m=-0.30,
                price_change_3m=-0.30,
                price_change_6m=-0.30,
                relative_strength=0,
                trend_strength=0,
            ),
            -1.0,
            1.0,
        ),
        (
            momentum_inputs(
                price_change_1m=0.30,
                price_change_3m=0.30,
                price_change_6m=0.30,
                relative_strength=100,
                trend_strength=1,
            ),
            2.0,
            1.0,
        ),
        (
            momentum_inputs(
                price_change_1m=-0.30,
                price_change_3m=-0.30,
                price_change_6m=0.30,
                relative_strength=100,
                trend_strength=1,
            ),
            0.50,
            0.66,
        ),
    ],
)
def test_confidence_boundaries_are_clamped_and_rounded(
    inputs: MomentumInputs,
    momentum_score: float,
    expected: float,
) -> None:
    """Confidence should remain deterministic at score and agreement boundaries."""
    assert MomentumCalculator.confidence_for(inputs, momentum_score) == expected


def test_calculator_evidence_is_human_readable() -> None:
    """Evidence should explain the core momentum components."""
    snapshot = MomentumCalculator().calculate(
        momentum_inputs(
            price_change_1m=0.09,
            price_change_3m=0.15,
            price_change_6m=0.28,
            relative_strength=82,
            trend_strength=0.80,
        )
    )

    assert "Strong 6-month trend." in snapshot.evidence
    assert "Relative strength above market." in snapshot.evidence
    assert "Short-term momentum accelerating." in snapshot.evidence
    assert all(item and item == item.strip() for item in snapshot.evidence)


@pytest.mark.parametrize(
    ("price_change_6m", "expected"),
    [
        (0.20, "Strong 6-month trend."),
        (0.08, "Positive 6-month trend."),
        (-0.20, "Strong negative 6-month trend."),
        (-0.08, "Negative 6-month trend."),
        (0.0799, "6-month trend is neutral."),
    ],
)
def test_six_month_evidence_thresholds_are_inclusive(
    price_change_6m: float,
    expected: str,
) -> None:
    """Six-month evidence should be stable at exact threshold values."""
    assert MomentumCalculator._six_month_evidence(price_change_6m) == expected


@pytest.mark.parametrize(
    ("relative_strength", "expected"),
    [
        (70, "Relative strength above market."),
        (30, "Relative strength below market."),
        (69.999, "Relative strength near market."),
        (30.001, "Relative strength near market."),
    ],
)
def test_relative_strength_evidence_thresholds_are_inclusive(
    relative_strength: float,
    expected: str,
) -> None:
    """Relative-strength evidence should be stable at exact threshold values."""
    assert MomentumCalculator._relative_strength_evidence(relative_strength) == expected


@pytest.mark.parametrize(
    ("price_change_1m", "price_change_3m", "expected"),
    [
        (0.0601, 0.12, "Short-term momentum accelerating."),
        (0.0199, 0.12, "Short-term momentum decelerating."),
        (0.06, 0.12, "Short-term momentum aligned with medium-term trend."),
        (0.02, 0.12, "Short-term momentum aligned with medium-term trend."),
    ],
)
def test_short_term_evidence_uses_strict_acceleration_boundaries(
    price_change_1m: float,
    price_change_3m: float,
    expected: str,
) -> None:
    """Short-term evidence should only flip outside the tolerance band."""
    assert (
        MomentumCalculator._short_term_evidence(
            momentum_inputs(
                price_change_1m=price_change_1m,
                price_change_3m=price_change_3m,
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    ("trend_strength", "expected"),
    [
        (0.70, "Trend strength is strong."),
        (0.30, "Trend strength is weak."),
        (0.6999, "Trend strength is moderate."),
        (0.3001, "Trend strength is moderate."),
    ],
)
def test_trend_strength_evidence_thresholds_are_inclusive(
    trend_strength: float,
    expected: str,
) -> None:
    """Trend-strength evidence should be stable at exact threshold values."""
    assert MomentumCalculator._trend_strength_evidence(trend_strength) == expected


def test_evidence_generation_order_is_deterministic() -> None:
    """Evidence should keep a stable order for downstream rendering and review."""
    inputs = momentum_inputs(
        price_change_1m=-0.04,
        price_change_3m=-0.12,
        price_change_6m=-0.21,
        relative_strength=22,
        trend_strength=0.20,
    )

    evidence = MomentumCalculator.evidence_for(
        inputs,
        MomentumRegime.STRONG_DOWNTREND,
        ReversalRisk.MEDIUM,
    )

    assert evidence == (
        "Strong negative 6-month trend.",
        "Relative strength below market.",
        "Short-term momentum aligned with medium-term trend.",
        "Trend strength is weak.",
        "Momentum regime classified as strong_downtrend.",
        "Reversal risk classified as medium.",
    )


def test_calculator_outputs_are_deterministic() -> None:
    """Identical inputs should produce identical snapshots."""
    calculator = MomentumCalculator()
    inputs = momentum_inputs(
        price_change_1m=0.03,
        price_change_3m=0.09,
        price_change_6m=0.16,
        relative_strength=68,
        trend_strength=0.64,
    )

    assert calculator.calculate(inputs) == calculator.calculate(inputs)


def test_calculator_has_no_external_dependencies() -> None:
    """The calculation layer should remain pure business logic."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "service",
        "database",
        "sqlite",
        "llm",
        "context",
        "recommendation",
        "trading",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[MomentumCalculator.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    snapshot = MomentumCalculator().calculate(momentum_inputs())

    assert isinstance(snapshot, MomentumSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_public_calculator_is_exported_from_momentum_package() -> None:
    """The package should expose the deterministic calculator."""
    import parakeetnest.intelligence.momentum as momentum

    assert momentum.MomentumCalculator is MomentumCalculator
