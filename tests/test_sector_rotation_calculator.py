"""Tests for deterministic sector rotation calculations."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.sector_rotation import (
    SectorIdentifier,
    SectorPerformance,
    SectorRotationCalculator,
    SectorRotationClassification,
    SectorRotationSnapshot,
)


AS_OF_DATE = date(2026, 6, 30)


def performance(
    sector_id: str,
    name: str,
    *,
    period_return: float | None,
    benchmark_return: float | None = 0.0,
    relative_return: float | None,
) -> SectorPerformance:
    return SectorPerformance(
        sector=SectorIdentifier(sector_id=sector_id, name=name),
        period_return=period_return,
        benchmark_return=benchmark_return,
        relative_return=relative_return,
        as_of_date=AS_OF_DATE,
        window_days=63,
    )


def signals_by_sector(
    snapshot: SectorRotationSnapshot,
) -> dict[str, SectorRotationClassification]:
    return {
        signal.sector.sector_id: signal.classification for signal in snapshot.signals
    }


def test_calculator_applies_relative_return_classification_rules() -> None:
    """Relative return thresholds should map to stable rotation states."""
    calculator = SectorRotationCalculator()
    snapshot = calculator.calculate(
        [
            performance(
                "leading",
                "Leading",
                period_return=0.10,
                relative_return=0.0501,
            ),
            performance(
                "improving",
                "Improving",
                period_return=0.04,
                relative_return=0.05,
            ),
            performance(
                "neutral_zero",
                "Neutral Zero",
                period_return=0.00,
                relative_return=0.0,
            ),
            performance(
                "weakening_floor",
                "Weakening Floor",
                period_return=-0.01,
                relative_return=-0.05,
            ),
            performance(
                "lagging",
                "Lagging",
                period_return=-0.08,
                relative_return=-0.0501,
            ),
            performance(
                "unknown",
                "Unknown",
                period_return=0.02,
                relative_return=None,
            ),
        ],
        as_of_date=AS_OF_DATE,
    )

    assert signals_by_sector(snapshot) == {
        "leading": SectorRotationClassification.LEADING,
        "improving": SectorRotationClassification.IMPROVING,
        "neutral_zero": SectorRotationClassification.NEUTRAL,
        "weakening_floor": SectorRotationClassification.WEAKENING,
        "lagging": SectorRotationClassification.LAGGING,
        "unknown": SectorRotationClassification.UNKNOWN,
    }


def test_calculator_applies_simple_momentum_rules() -> None:
    """Momentum direction should use deterministic absolute return rules."""
    calculator = SectorRotationCalculator()
    snapshot = calculator.calculate(
        [
            performance("rising", "Rising", period_return=0.01, relative_return=0.01),
            performance("flat", "Flat", period_return=0.0, relative_return=0.0),
            performance(
                "falling",
                "Falling",
                period_return=-0.01,
                relative_return=-0.01,
            ),
            performance("missing", "Missing", period_return=None, relative_return=0.02),
        ],
        as_of_date=AS_OF_DATE,
    )

    directions = {
        signal.sector.sector_id: signal.momentum.direction
        for signal in snapshot.signals
        if signal.momentum is not None
    }

    assert directions == {
        "rising": "rising",
        "flat": "flat",
        "falling": "falling",
        "missing": "flat",
    }


def test_calculator_assigns_simple_confidence_levels() -> None:
    """Confidence should reflect completeness of deterministic evidence."""
    calculator = SectorRotationCalculator()
    snapshot = calculator.calculate(
        [
            performance("high", "High", period_return=0.02, relative_return=0.01),
            performance(
                "medium_period",
                "Medium Period",
                period_return=None,
                relative_return=0.01,
            ),
            performance(
                "medium_benchmark",
                "Medium Benchmark",
                period_return=0.02,
                benchmark_return=None,
                relative_return=0.01,
            ),
            performance("low", "Low", period_return=0.02, relative_return=None),
        ],
        as_of_date=AS_OF_DATE,
    )

    confidence = {
        signal.sector.sector_id: signal.confidence for signal in snapshot.signals
    }

    assert confidence == {
        "high": "high",
        "medium_period": "medium",
        "medium_benchmark": "medium",
        "low": "low",
    }


def test_calculator_populates_snapshot_signals_and_metadata() -> None:
    """The snapshot should include relative strength, momentum, and evidence."""
    calculator = SectorRotationCalculator()
    snapshot = calculator.calculate(
        [
            performance("energy", "Energy", period_return=0.08, relative_return=0.06),
            performance(
                "utilities",
                "Utilities",
                period_return=-0.03,
                relative_return=-0.07,
            ),
        ],
        as_of_date=AS_OF_DATE,
    )

    energy = next(
        signal for signal in snapshot.signals if signal.sector.sector_id == "energy"
    )
    utilities = next(
        signal for signal in snapshot.signals if signal.sector.sector_id == "utilities"
    )

    assert snapshot.as_of_date == AS_OF_DATE
    assert snapshot.source == "sector_rotation_calculator"
    assert snapshot.summary is not None
    assert "1 leading" in snapshot.summary
    assert "1 lagging" in snapshot.summary
    assert energy.relative_strength is not None
    assert energy.relative_strength.score == 0.06
    assert energy.relative_strength.rank == 1
    assert energy.momentum is not None
    assert energy.momentum.direction == "rising"
    assert energy.performance is not None
    assert energy.evidence
    assert energy.catalysts
    assert utilities.risks


def test_calculator_is_deterministic_for_same_inputs() -> None:
    """Identical inputs and dates should produce equal snapshots."""
    calculator = SectorRotationCalculator()
    sector_performance = [
        performance("energy", "Energy", period_return=0.08, relative_return=0.06),
        performance(
            "utilities",
            "Utilities",
            period_return=-0.03,
            relative_return=-0.07,
        ),
    ]

    first = calculator.calculate(sector_performance, as_of_date=AS_OF_DATE)
    second = calculator.calculate(sector_performance, as_of_date=AS_OF_DATE)

    assert first == second


def test_calculator_has_no_provider_or_network_dependencies() -> None:
    """The calculation layer should remain pure and provider-neutral."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "provider",
        "sdk",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp"}
    source = inspect.getsource(sys.modules[SectorRotationCalculator.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    calculator = SectorRotationCalculator()
    snapshot = calculator.calculate([], as_of_date=AS_OF_DATE)

    assert isinstance(snapshot, SectorRotationSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_public_calculator_is_exported_from_sector_rotation_package() -> None:
    """The package should expose the deterministic calculator."""
    import parakeetnest.intelligence.sector_rotation as sector_rotation

    assert sector_rotation.SectorRotationCalculator is SectorRotationCalculator
