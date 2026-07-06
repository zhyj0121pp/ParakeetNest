"""Tests for deterministic position consensus building."""

from __future__ import annotations

from pathlib import Path

from parakeetnest.decision import (
    CommitteePositionReview,
    ConfidenceLevel,
    DecisionUrgency,
    PositionContext,
    PositionRecommendation,
)
from parakeetnest.services import PositionConsensusBuilder


def test_unanimous_no_action_or_hold_produces_no_action() -> None:
    decision = PositionConsensusBuilder().build(
        _position_context(risk_notes=()),
        (
            _review("Dongdong", PositionRecommendation.HOLD),
            _review("Xixi", PositionRecommendation.NO_ACTION),
            _review("Youyou", PositionRecommendation.HOLD),
        ),
    )

    assert decision.recommendation is PositionRecommendation.NO_ACTION
    assert decision.action_required is False
    assert decision.urgency is DecisionUrgency.NONE
    assert decision.human_review_required is False


def test_buy_more_consensus_produces_required_action() -> None:
    decision = PositionConsensusBuilder().build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.BUY_MORE),
            _review("Xixi", PositionRecommendation.BUY_MORE),
            _review("Youyou", PositionRecommendation.HOLD),
        ),
    )

    assert decision.recommendation is PositionRecommendation.BUY_MORE
    assert decision.action_required is True
    assert decision.human_review_required is True


def test_sell_and_trim_require_human_review() -> None:
    builder = PositionConsensusBuilder()

    sell_decision = builder.build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.SELL),
            _review("Xixi", PositionRecommendation.SELL),
            _review("Youyou", PositionRecommendation.TRIM),
        ),
    )
    trim_decision = builder.build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.TRIM),
            _review("Xixi", PositionRecommendation.TRIM),
            _review("Youyou", PositionRecommendation.SELL),
        ),
    )

    assert sell_decision.recommendation is PositionRecommendation.SELL
    assert sell_decision.human_review_required is True
    assert trim_decision.recommendation is PositionRecommendation.TRIM
    assert trim_decision.human_review_required is True


def test_conflicting_recommendations_reduce_confidence() -> None:
    aligned = PositionConsensusBuilder().build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.BUY_MORE, ConfidenceLevel.HIGH),
            _review("Xixi", PositionRecommendation.BUY_MORE, ConfidenceLevel.HIGH),
            _review("Youyou", PositionRecommendation.BUY_MORE, ConfidenceLevel.HIGH),
        ),
    )
    conflicted = PositionConsensusBuilder().build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.BUY_MORE, ConfidenceLevel.HIGH),
            _review("Xixi", PositionRecommendation.HOLD, ConfidenceLevel.HIGH),
            _review("Youyou", PositionRecommendation.SELL, ConfidenceLevel.HIGH),
        ),
    )

    assert aligned.confidence is ConfidenceLevel.HIGH
    assert conflicted.confidence is ConfidenceLevel.LOW


def test_youyou_risk_objection_increases_urgency() -> None:
    without_risk_objection = PositionConsensusBuilder().build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.TRIM),
            _review("Xixi", PositionRecommendation.TRIM),
            _review("Youyou", PositionRecommendation.HOLD),
        ),
    )
    with_risk_objection = PositionConsensusBuilder().build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.TRIM),
            _review("Xixi", PositionRecommendation.HOLD),
            _review("Youyou", PositionRecommendation.TRIM),
        ),
    )

    assert without_risk_objection.urgency is DecisionUrgency.LOW
    assert with_risk_objection.urgency is DecisionUrgency.HIGH


def test_all_hold_with_material_risk_notes_produces_watch() -> None:
    decision = PositionConsensusBuilder().build(
        _position_context(risk_notes=("Position is above target allocation.",)),
        (
            _review("Dongdong", PositionRecommendation.HOLD),
            _review("Xixi", PositionRecommendation.HOLD),
            _review("Youyou", PositionRecommendation.NO_ACTION),
        ),
    )

    assert decision.recommendation is PositionRecommendation.WATCH
    assert decision.action_required is False
    assert decision.urgency is DecisionUrgency.LOW


def test_output_includes_all_three_committee_opinions() -> None:
    decision = PositionConsensusBuilder().build(
        _position_context(),
        (
            _review("Dongdong", PositionRecommendation.BUY_MORE),
            _review("Xixi", PositionRecommendation.HOLD),
            _review("Youyou", PositionRecommendation.TRIM),
        ),
    )

    assert "Dongdong thesis" in decision.dongdong_opinion
    assert "Xixi thesis" in decision.xixi_opinion
    assert "Youyou thesis" in decision.youyou_opinion
    assert decision.factual_evidence
    assert decision.risks


def test_builder_has_no_llm_provider_dependency() -> None:
    source = Path("src/parakeetnest/services/position_consensus.py").read_text(
        encoding="utf-8"
    )

    assert "LLMProvider" not in source
    assert "llm_provider" not in source
    assert "parakeetnest.llm" not in source


def test_builder_has_no_provider_specific_references() -> None:
    source = Path("src/parakeetnest/services/position_consensus.py").read_text(
        encoding="utf-8"
    )

    provider_terms = (
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "robinhood",
        "yahoo",
        "gmail",
    )
    assert all(term not in source.lower() for term in provider_terms)


def _position_context(
    *,
    risk_notes: tuple[str, ...] = ("Position is a large portfolio weight.",),
) -> PositionContext:
    return PositionContext(
        symbol="NVDA",
        company_name="NVIDIA Corporation",
        quantity=2,
        market_value=1840,
        portfolio_weight=0.25,
        cost_basis=820,
        unrealized_gain_loss=200,
        current_price=920,
        recent_price_change=0.03,
        relevant_news=("Blackwell demand remains strong.",),
        relevant_research=("Prior thesis favors durable AI infrastructure demand.",),
        risk_notes=risk_notes,
        valuation_notes=("Premium multiple requires durable earnings growth.",),
        momentum_notes=("Trend remains positive.",),
        portfolio_notes=("Largest current holding.",),
    )


def _review(
    agent_name: str,
    recommendation: PositionRecommendation,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> CommitteePositionReview:
    return CommitteePositionReview(
        symbol="NVDA",
        agent_name=agent_name,
        thesis=f"{agent_name} thesis for the current position.",
        concerns=(f"{agent_name} concern to monitor.",),
        recommendation=recommendation,
        confidence=confidence,
        evidence_refs=(f"{agent_name} evidence reference.",),
    )
