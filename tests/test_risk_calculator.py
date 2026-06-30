"""Tests for deterministic provider-neutral risk calculations."""

from __future__ import annotations

import inspect
import sys
from datetime import date

import pytest

from parakeetnest.intelligence.risk import (
    RiskAssessment,
    RiskCalculator,
    RiskCategory,
    RiskLevel,
    RiskSignal,
)


AS_OF_DATE = date(2026, 6, 30)


def signal(
    score: float,
    *,
    level: RiskLevel | str | None = None,
    category: RiskCategory = RiskCategory.MARKET,
    label: str = "Risk signal",
    evidence: tuple[str, ...] = ("risk evidence",),
    metadata: dict[str, object] | None = None,
) -> RiskSignal:
    return RiskSignal(
        category=category,
        level=level or RiskLevel.LOW,
        score=score,
        label=label,
        description="Signal description.",
        evidence=evidence,
        metadata=metadata or {},
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.00, RiskLevel.LOW),
        (0.20, RiskLevel.LOW),
        (0.2001, RiskLevel.MODERATE),
        (0.40, RiskLevel.MODERATE),
        (0.4001, RiskLevel.ELEVATED),
        (0.60, RiskLevel.ELEVATED),
        (0.6001, RiskLevel.HIGH),
        (0.80, RiskLevel.HIGH),
        (0.8001, RiskLevel.EXTREME),
        (1.00, RiskLevel.EXTREME),
    ],
)
def test_score_maps_to_correct_risk_level(
    score: float,
    expected: RiskLevel,
) -> None:
    """Risk score thresholds should be stable and deterministic."""
    assessment = RiskCalculator().calculate(
        [signal(score)],
        as_of_date=AS_OF_DATE,
    )

    assert assessment.overall_score == score
    assert assessment.overall_level is expected
    assert assessment.signals[0].level is expected


def test_empty_signals_return_low_risk_assessment() -> None:
    """No signals should produce the neutral low-risk default."""
    assessment = RiskCalculator().calculate([], as_of_date=AS_OF_DATE)

    assert assessment.overall_level is RiskLevel.LOW
    assert assessment.overall_score == 0.0
    assert assessment.signals == []
    assert assessment.as_of_date == AS_OF_DATE
    assert assessment.source == "risk_calculator"


def test_average_score_computes_overall_score() -> None:
    """The default aggregate score should be the mean signal score."""
    assessment = RiskCalculator().calculate(
        [
            signal(0.2, category=RiskCategory.MARKET),
            signal(0.4, category=RiskCategory.VALUATION),
            signal(0.6, category=RiskCategory.MACRO),
        ],
        as_of_date=AS_OF_DATE,
    )

    assert assessment.overall_score == pytest.approx(0.4)
    assert assessment.overall_level is RiskLevel.MODERATE


def test_score_below_zero_is_clamped() -> None:
    """Calculator output should normalize scores into the supported range."""
    assessment = RiskCalculator().calculate([signal(-0.25)], as_of_date=AS_OF_DATE)

    assert assessment.overall_score == 0.0
    assert assessment.overall_level is RiskLevel.LOW
    assert assessment.signals[0].score == 0.0
    assert assessment.signals[0].level is RiskLevel.LOW


def test_score_above_one_is_clamped() -> None:
    """Calculator output should normalize scores into the supported range."""
    assessment = RiskCalculator().calculate([signal(1.25)], as_of_date=AS_OF_DATE)

    assert assessment.overall_score == 1.0
    assert assessment.overall_level is RiskLevel.EXTREME
    assert assessment.signals[0].score == 1.0
    assert assessment.signals[0].level is RiskLevel.EXTREME


def test_extreme_signal_raises_overall_level_to_at_least_high() -> None:
    """A severe tail signal should keep aggregate severity at least high."""
    assessment = RiskCalculator().calculate(
        [
            signal(0.1, category=RiskCategory.MARKET),
            signal(0.1, level=RiskLevel.EXTREME, category=RiskCategory.LIQUIDITY),
        ],
        as_of_date=AS_OF_DATE,
    )

    assert assessment.overall_score == pytest.approx(0.1)
    assert assessment.overall_level is RiskLevel.HIGH


def test_metadata_and_evidence_are_preserved() -> None:
    """Normalized signals should retain provider-neutral supporting context."""
    assessment = RiskCalculator().calculate(
        [
            signal(
                0.42,
                category=RiskCategory.SECTOR,
                label="Sector risk",
                evidence=("weak relative strength", "defensive breadth fading"),
                metadata={"window_days": 63, "method": "normalized_signal"},
            )
        ],
        as_of_date=AS_OF_DATE,
    )

    normalized_signal = assessment.signals[0]

    assert normalized_signal.evidence == (
        "weak relative strength",
        "defensive breadth fading",
    )
    assert normalized_signal.metadata == {
        "window_days": 63,
        "method": "normalized_signal",
    }


def test_calculator_has_no_provider_or_network_dependencies() -> None:
    """The risk calculator should remain pure and provider-neutral."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "provider",
        "sec",
        "macro",
        "valuation",
        "trading",
        "recommendation",
        "llm",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp"}
    source = inspect.getsource(sys.modules[RiskCalculator.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    calculator = RiskCalculator()
    assessment = calculator.calculate([], as_of_date=AS_OF_DATE)

    assert isinstance(assessment, RiskAssessment)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_public_calculator_is_exported_from_risk_package() -> None:
    """The package should expose the deterministic calculator."""
    import parakeetnest.intelligence.risk as risk

    assert risk.RiskCalculator is RiskCalculator
