"""Tests for provider-neutral position committee review execution."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from parakeetnest.decision import (
    CommitteePositionReview,
    ConfidenceLevel,
    PositionContext,
    PositionRecommendation,
)
from parakeetnest.llm import LLMRequest, LLMResponse
from parakeetnest.services import PositionCommitteeReviewRunner


@dataclass
class RecordingLLMProvider:
    """Test fake that records requests and returns schema-valid reviews."""

    name: str = "recording-fake"
    requests: list[LLMRequest] = field(default_factory=list)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        agent_name = request.metadata["agent_name"]
        return LLMResponse(
            content=json.dumps(
                {
                    "symbol": request.metadata["symbol"],
                    "agent_name": agent_name,
                    "thesis": f"{agent_name} thesis from supplied context.",
                    "concerns": [f"{agent_name} concern from supplied context."],
                    "recommendation": "hold",
                    "confidence": "medium",
                    "evidence_refs": [f"{agent_name} prompt evidence."],
                }
            ),
            model=request.model,
            provider_name=self.name,
        )


def test_runner_builds_and_runs_exactly_three_reviews() -> None:
    provider = RecordingLLMProvider()

    reviews = PositionCommitteeReviewRunner(llm_provider=provider).run(
        _position_context()
    )

    assert len(reviews) == 3
    assert len(provider.requests) == 3
    assert all(isinstance(review, CommitteePositionReview) for review in reviews)


def test_runner_preserves_dongdong_xixi_youyou_order() -> None:
    provider = RecordingLLMProvider()

    reviews = PositionCommitteeReviewRunner(llm_provider=provider).run(
        _position_context()
    )

    assert [request.metadata["persona_id"] for request in provider.requests] == [
        "dongdong",
        "xixi",
        "youyou",
    ]
    assert [review.agent_name for review in reviews] == ["Dongdong", "Xixi", "Youyou"]


def test_llm_provider_is_called_once_per_prompt_with_position_review_schema() -> None:
    provider = RecordingLLMProvider()

    PositionCommitteeReviewRunner(llm_provider=provider).run(_position_context())

    assert len(provider.requests) == 3
    assert all("CommitteePositionReview" in request.prompt for request in provider.requests)
    assert all(request.response_schema is not None for request in provider.requests)
    assert all(request.temperature == 0.0 for request in provider.requests)


def test_parser_returns_committee_position_review_objects() -> None:
    provider = RecordingLLMProvider()

    reviews = PositionCommitteeReviewRunner(llm_provider=provider).run(
        _position_context()
    )

    assert all(review.symbol == "NVDA" for review in reviews)
    assert all(review.recommendation is PositionRecommendation.HOLD for review in reviews)
    assert all(review.confidence is ConfidenceLevel.MEDIUM for review in reviews)
    assert all(review.evidence_refs for review in reviews)


def test_runner_does_not_produce_position_decision() -> None:
    provider = RecordingLLMProvider()

    reviews = PositionCommitteeReviewRunner(llm_provider=provider).run(
        _position_context()
    )

    assert all(not hasattr(review, "final_rationale") for review in reviews)
    assert all(not hasattr(review, "action_required") for review in reviews)
    assert all(not hasattr(review, "human_review_required") for review in reviews)


def test_runner_has_no_provider_specific_references() -> None:
    source = Path(
        "src/parakeetnest/services/position_committee_review.py"
    ).read_text(encoding="utf-8")

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


def _position_context() -> PositionContext:
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
        risk_notes=("Position is a large portfolio weight.",),
        valuation_notes=("Premium multiple requires durable earnings growth.",),
        momentum_notes=("Trend remains positive.",),
        portfolio_notes=("Largest current holding.",),
    )
