"""Tests for the complete investment committee product skeleton."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from parakeetnest.committee import (
    DEFAULT_INVESTMENT_COMMITTEE,
    InvestmentCommitteeDecision,
    InvestmentCommitteeReport,
    InvestmentCommitteeRequest,
)
from parakeetnest.models import ConfidenceLevel, InvestmentHorizon


def test_investment_committee_request_model_normalizes_core_fields() -> None:
    """Request models should capture the user-facing review inputs."""
    request = InvestmentCommitteeRequest(
        ticker=" nvda ",
        topic=" AI infrastructure durability ",
        time_horizon="1_year",
        user_question=" Should we add after earnings? ",
        portfolio_context_notes=" Already a top-five position. ",
    )

    assert request.ticker == "NVDA"
    assert request.topic == "AI infrastructure durability"
    assert request.time_horizon is InvestmentHorizon.ONE_YEAR
    assert request.user_question == "Should we add after earnings?"
    assert request.portfolio_context_notes == "Already a top-five position."

    with pytest.raises(FrozenInstanceError):
        request.ticker = "AMD"


def test_investment_committee_report_model_normalizes_enums() -> None:
    """Report models should hold all committee views and the final decision."""
    report = InvestmentCommitteeReport(
        ticker=" msft ",
        topic="Cloud and AI margin durability",
        time_horizon=InvestmentHorizon.SIX_MONTHS,
        macro_view="Rates remain a valuation headwind.",
        sector_view="Software quality factors remain supported.",
        fundamental_view="Revenue quality and margins remain strong.",
        valuation_view="Multiple leaves limited room for disappointment.",
        risk_view="Execution and capex risks require monitoring.",
        momentum_sentiment_view="Momentum remains constructive.",
        bull_case="AI demand expands operating leverage.",
        bear_case="Capex intensity compresses free cash flow.",
        key_risks=("Valuation compression", "AI infrastructure overbuild"),
        decision="hold",
        confidence="medium",
        recommended_action="Hold existing position and watch capex commentary.",
    )

    assert report.ticker == "MSFT"
    assert report.time_horizon is InvestmentHorizon.SIX_MONTHS
    assert report.decision is InvestmentCommitteeDecision.HOLD
    assert report.confidence is ConfidenceLevel.MEDIUM
    assert report.key_risks == (
        "Valuation compression",
        "AI infrastructure overbuild",
    )


def test_investment_committee_decision_enum_values_are_stable() -> None:
    """Decision values should match the product contract."""
    assert [decision.value for decision in InvestmentCommitteeDecision] == [
        "buy",
        "hold",
        "watch",
        "avoid",
    ]


def test_default_investment_committee_composition_is_complete() -> None:
    """The default committee should include each product role in order."""
    assert [member.name for member in DEFAULT_INVESTMENT_COMMITTEE] == [
        "Macro Strategist",
        "Sector Analyst",
        "Fundamental Analyst",
        "Valuation Analyst",
        "Risk Manager",
        "Momentum / Sentiment Analyst",
        "Chair / CIO",
    ]
    assert all(member.role for member in DEFAULT_INVESTMENT_COMMITTEE)
