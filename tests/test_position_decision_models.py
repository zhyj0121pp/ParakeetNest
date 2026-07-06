"""Tests for Phase II position-level investment decision models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from parakeetnest.decision import (
    CommitteePositionReview,
    ConfidenceLevel,
    DecisionUrgency,
    NewOpportunity,
    PortfolioDecisionSummary,
    PositionDecision,
    PositionRecommendation,
)


def test_position_recommendation_values_are_stable() -> None:
    """Position recommendations should be provider-neutral decision values."""
    assert PositionRecommendation.BUY_MORE.value == "buy_more"
    assert PositionRecommendation.HOLD.value == "hold"
    assert PositionRecommendation.TRIM.value == "trim"
    assert PositionRecommendation.SELL.value == "sell"
    assert PositionRecommendation.WATCH.value == "watch"
    assert PositionRecommendation.NO_ACTION.value == "no_action"


def test_decision_urgency_values_are_stable() -> None:
    """Urgency values should describe review priority, not execution."""
    assert DecisionUrgency.HIGH.value == "high"
    assert DecisionUrgency.MEDIUM.value == "medium"
    assert DecisionUrgency.LOW.value == "low"
    assert DecisionUrgency.NONE.value == "none"


def test_position_decision_has_required_field_boundary() -> None:
    """PositionDecision should expose the Phase II decision experience fields."""
    assert tuple(field.name for field in fields(PositionDecision)) == (
        "symbol",
        "company_name",
        "recommendation",
        "action_required",
        "urgency",
        "final_rationale",
        "dongdong_opinion",
        "xixi_opinion",
        "youyou_opinion",
        "factual_evidence",
        "risks",
        "confidence",
        "human_review_required",
    )


def test_position_decision_construction_normalizes_basic_invariants() -> None:
    """A position decision should normalize enums, symbol, and collections."""
    decision = PositionDecision(
        symbol=" nvda ",
        company_name=" NVIDIA Corporation ",
        recommendation="BUY_MORE",
        action_required=1,
        urgency="HIGH",
        final_rationale="Committee sees durable AI demand.",
        dongdong_opinion="Opportunity remains attractive.",
        xixi_opinion="Fundamentals remain strong.",
        youyou_opinion="Sizing risk requires review.",
        factual_evidence=[" Revenue growth accelerated. ", ""],  # type: ignore[arg-type]
        risks=[" Valuation compression. "],  # type: ignore[arg-type]
        confidence="MEDIUM",
        human_review_required=1,
    )

    assert decision.symbol == "NVDA"
    assert decision.company_name == "NVIDIA Corporation"
    assert decision.recommendation is PositionRecommendation.BUY_MORE
    assert decision.action_required is True
    assert decision.urgency is DecisionUrgency.HIGH
    assert decision.factual_evidence == ("Revenue growth accelerated.",)
    assert decision.risks == ("Valuation compression.",)
    assert decision.confidence is ConfidenceLevel.MEDIUM
    assert decision.human_review_required is True

    with pytest.raises(FrozenInstanceError):
        decision.symbol = "AMD"


def test_position_decision_requires_evidence_and_risks() -> None:
    """Every position recommendation must carry evidence and risk notes."""
    with pytest.raises(ValueError, match="factual_evidence is required"):
        PositionDecision(
            symbol="MSFT",
            company_name="Microsoft",
            recommendation=PositionRecommendation.HOLD,
            action_required=False,
            urgency=DecisionUrgency.LOW,
            final_rationale="Maintain current position.",
            dongdong_opinion="Limited near-term upside.",
            xixi_opinion="Quality remains high.",
            youyou_opinion="Risk is manageable.",
            factual_evidence=(),
            risks=("Multiple risk.",),
            confidence=ConfidenceLevel.HIGH,
            human_review_required=False,
        )

    with pytest.raises(ValueError, match="risks is required"):
        PositionDecision(
            symbol="MSFT",
            company_name="Microsoft",
            recommendation=PositionRecommendation.HOLD,
            action_required=False,
            urgency=DecisionUrgency.LOW,
            final_rationale="Maintain current position.",
            dongdong_opinion="Limited near-term upside.",
            xixi_opinion="Quality remains high.",
            youyou_opinion="Risk is manageable.",
            factual_evidence=("Cash flow remains strong.",),
            risks=(),
            confidence=ConfidenceLevel.HIGH,
            human_review_required=False,
        )


def test_committee_position_review_normalizes_review_fields() -> None:
    """Committee reviews should preserve each agent's thesis and evidence refs."""
    review = CommitteePositionReview(
        symbol=" aapl ",
        agent_name=" Xixi ",
        thesis=" Services growth supports quality. ",
        concerns=[" Hardware cycle risk. "],  # type: ignore[arg-type]
        recommendation="HOLD",
        confidence="high",
        evidence_refs=["latest financial snapshot"],
    )

    assert review.symbol == "AAPL"
    assert review.agent_name == "Xixi"
    assert review.thesis == "Services growth supports quality."
    assert review.concerns == ("Hardware cycle risk.",)
    assert review.recommendation is PositionRecommendation.HOLD
    assert review.confidence is ConfidenceLevel.HIGH
    assert review.evidence_refs == ("latest financial snapshot",)


def test_portfolio_decision_summary_normalizes_collections() -> None:
    """Portfolio summaries should keep action and no-action lists immutable."""
    summary = PortfolioDecisionSummary(
        overall_portfolio_view="Balanced but concentrated.",
        concentration_risks=[" NVDA weight elevated. "],  # type: ignore[arg-type]
        sector_exposure_notes=[" Technology overweight. "],  # type: ignore[arg-type]
        cash_allocation_notes=[" Cash supports optionality. "],  # type: ignore[arg-type]
        action_items=["Trim oversized position."],  # type: ignore[arg-type]
        no_action_positions=[" msft ", " aapl "],  # type: ignore[arg-type]
    )

    assert summary.concentration_risks == ("NVDA weight elevated.",)
    assert summary.sector_exposure_notes == ("Technology overweight.",)
    assert summary.cash_allocation_notes == ("Cash supports optionality.",)
    assert summary.action_items == ("Trim oversized position.",)
    assert summary.no_action_positions == ("MSFT", "AAPL")


def test_new_opportunity_construction_normalizes_basic_invariants() -> None:
    """New opportunities should carry rationale, risks, action, and confidence."""
    opportunity = NewOpportunity(
        symbol=" tsm ",
        company_name=" Taiwan Semiconductor Manufacturing ",
        opportunity_type="watchlist candidate",
        rationale="Leading foundry exposure.",
        risks=["Geopolitical risk."],
        suggested_action="WATCH",
        confidence="LOW",
    )

    assert opportunity.symbol == "TSM"
    assert opportunity.company_name == "Taiwan Semiconductor Manufacturing"
    assert opportunity.opportunity_type == "watchlist candidate"
    assert opportunity.risks == ("Geopolitical risk.",)
    assert opportunity.suggested_action is PositionRecommendation.WATCH
    assert opportunity.confidence is ConfidenceLevel.LOW

    with pytest.raises(ValueError, match="risks is required"):
        NewOpportunity(
            symbol="TSM",
            company_name="Taiwan Semiconductor Manufacturing",
            opportunity_type="watchlist candidate",
            rationale="Leading foundry exposure.",
            risks=(),
            suggested_action=PositionRecommendation.WATCH,
            confidence=ConfidenceLevel.LOW,
        )
