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
