"""Tests for Risk Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date
from types import MappingProxyType

import pytest

from parakeetnest.intelligence.risk import (
    RiskAssessment,
    RiskCategory,
    RiskLevel,
    RiskSignal,
    RiskSummary,
)


AS_OF_DATE = date(2026, 6, 30)


def test_risk_level_values_are_stable() -> None:
    """Risk levels should describe severity, not providers."""
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MODERATE.value == "moderate"
    assert RiskLevel.ELEVATED.value == "elevated"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.EXTREME.value == "extreme"


def test_risk_category_values_are_stable() -> None:
    """Risk categories should remain provider-neutral."""
    assert RiskCategory.MARKET.value == "market"
    assert RiskCategory.SECTOR.value == "sector"
    assert RiskCategory.VALUATION.value == "valuation"
    assert RiskCategory.MACRO.value == "macro"
    assert RiskCategory.CONCENTRATION.value == "concentration"
    assert RiskCategory.VOLATILITY.value == "volatility"
    assert RiskCategory.DRAWDOWN.value == "drawdown"
    assert RiskCategory.LIQUIDITY.value == "liquidity"


def test_risk_signal_normalizes_fields_and_metadata() -> None:
    """Signals should capture severity, evidence, and optional metadata."""
    signal = RiskSignal(
        category="valuation",
        level="elevated",
        score=0.72,
        label=" Multiple expansion ",
        description=" Valuation is above normalized history. ",
        evidence=(" forward multiple above range ", ""),
        metadata={"percentile": 91},
    )

    assert signal.category is RiskCategory.VALUATION
    assert signal.level is RiskLevel.ELEVATED
    assert signal.score == 0.72
    assert signal.label == "Multiple expansion"
    assert signal.description == "Valuation is above normalized history."
    assert signal.evidence == ("forward multiple above range",)
    assert signal.metadata == {"percentile": 91}
    assert isinstance(signal.metadata, MappingProxyType)

    with pytest.raises(TypeError):
        signal.metadata["provider"] = "vendor"

    with pytest.raises(FrozenInstanceError):
        signal.label = "Changed"


def test_risk_assessment_aggregates_signals_and_normalizes_metadata() -> None:
    """Assessments should expose an overall level and score."""
    market_signal = RiskSignal(
        category=RiskCategory.MARKET,
        level=RiskLevel.HIGH,
        score=0.84,
        label="Market stress",
        description="Market breadth is weak.",
        evidence=("weak breadth",),
    )
    liquidity_signal = RiskSignal(
        category=RiskCategory.LIQUIDITY,
        level=RiskLevel.MODERATE,
        score=0.46,
        label="Liquidity",
        description="Trading conditions are mixed.",
    )

    assessment = RiskAssessment(
        overall_level="high",
        overall_score=0.81,
        signals=[market_signal, liquidity_signal],
        as_of_date=AS_OF_DATE,
        summary=" risk is elevated by market stress ",
        source=" risk scoring engine ",
    )

    assert assessment.overall_level is RiskLevel.HIGH
    assert assessment.overall_score == 0.81
    assert assessment.as_of_date == AS_OF_DATE
    assert assessment.summary == "risk is elevated by market stress"
    assert assessment.source == "risk scoring engine"
    assert assessment.signals == [liquidity_signal, market_signal]


def test_risk_summary_is_compact_and_prompt_ready() -> None:
    """Summaries should stay compact for later context rendering."""
    summary = RiskSummary(
        overall_level="moderate",
        overall_score=0.55,
        headline=" Risk is balanced ",
        top_risks=(" valuation reset ", ""),
        evidence=(" drawdown contained ",),
    )

    assert summary.overall_level is RiskLevel.MODERATE
    assert summary.overall_score == 0.55
    assert summary.headline == "Risk is balanced"
    assert summary.top_risks == ("valuation reset",)
    assert summary.evidence == ("drawdown contained",)


def test_risk_models_have_no_provider_specific_fields() -> None:
    """Risk models should avoid vendor-specific or prompt-specific structure."""
    forbidden_names = {
        "yahoo",
        "ticker",
        "symbol",
        "sec",
        "api",
        "database",
        "llm",
        "recommendation",
        "action",
    }

    for model in (RiskSignal, RiskAssessment, RiskSummary):
        field_names = {field.name.lower() for field in fields(model)}
        assert field_names.isdisjoint(forbidden_names)


def test_public_models_are_exported_from_risk_package() -> None:
    """The package should expose the public Risk Layer model surface."""
    import parakeetnest.intelligence.risk as risk

    assert risk.RiskLevel is RiskLevel
    assert risk.RiskCategory is RiskCategory
    assert risk.RiskSignal is RiskSignal
    assert risk.RiskAssessment is RiskAssessment
    assert risk.RiskSummary is RiskSummary


def test_invalid_risk_values_are_rejected() -> None:
    """Unknown enum strings should fail at the domain boundary."""
    with pytest.raises(ValueError):
        RiskSignal(
            category="sentiment",
            level=RiskLevel.LOW,
            score=0.1,
            label="Sentiment",
            description="Not a v1 risk category.",
        )

    with pytest.raises(ValueError):
        RiskAssessment(overall_level="critical", overall_score=1.0)
