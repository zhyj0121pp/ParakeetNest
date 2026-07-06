"""Tests for the one-position decision workflow service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from parakeetnest.context import (
    KnowledgeBaseSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    NewsContext,
    NewsItem,
)
from parakeetnest.decision import (
    CommitteePositionReview,
    ConfidenceLevel,
    DecisionUrgency,
    PositionContext,
    PositionDecision,
    PositionRecommendation,
)
from parakeetnest.services import PositionDecisionWorkflowService


@dataclass(frozen=True)
class ProviderNeutralPosition:
    symbol: str
    name: str
    quantity: float
    market_value: float
    weight: float


@dataclass
class FakeContextBuilder:
    calls: list[dict[str, object]] = field(default_factory=list)

    def build(self, position: object, **inputs: object) -> PositionContext:
        self.calls.append({"position": position, **inputs})
        return PositionContext(
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            quantity=2,
            market_value=1840,
            portfolio_weight=0.25,
            current_price=920,
            relevant_news=("Blackwell demand remains strong.",),
            relevant_research=("Thesis remains intact.",),
            risk_notes=("Position is a large portfolio weight.",),
            valuation_notes=("Premium multiple requires growth.",),
            momentum_notes=("Trend remains positive.",),
            portfolio_notes=("Largest current holding.",),
        )


@dataclass
class FakeReviewRunner:
    calls: list[PositionContext] = field(default_factory=list)

    def run(self, context: PositionContext) -> tuple[CommitteePositionReview, ...]:
        self.calls.append(context)
        return (
            _review("Dongdong", PositionRecommendation.BUY_MORE),
            _review("Xixi", PositionRecommendation.HOLD),
            _review("Youyou", PositionRecommendation.TRIM),
        )


@dataclass
class FakeConsensusBuilder:
    decision: PositionDecision = field(default_factory=lambda: _decision())
    calls: list[dict[str, object]] = field(default_factory=list)

    def build(
        self,
        context: PositionContext,
        reviews: tuple[CommitteePositionReview, ...],
    ) -> PositionDecision:
        self.calls.append({"context": context, "reviews": reviews})
        return self.decision


def test_workflow_builds_context_runs_committee_review_and_builds_consensus() -> None:
    context_builder = FakeContextBuilder()
    review_runner = FakeReviewRunner()
    consensus_builder = FakeConsensusBuilder()
    position = _position()
    market = MarketSnapshot(
        source="already-available-market",
        points=(MarketDataPoint(symbol="NVDA", source="already-available-market"),),
    )
    news = NewsContext(
        source="already-available-news",
        items=(NewsItem(symbol="NVDA", title="NVIDIA update", source="news"),),
    )
    knowledge_base = KnowledgeBaseSnapshot(
        research_notes=("NVDA thesis remains intact.",)
    )

    decision = PositionDecisionWorkflowService(
        context_builder=context_builder,  # type: ignore[arg-type]
        review_runner=review_runner,  # type: ignore[arg-type]
        consensus_builder=consensus_builder,  # type: ignore[arg-type]
    ).run(
        position,
        market=market,
        news=news,
        knowledge_base=knowledge_base,
        risk_notes=("Sizing risk.",),
        valuation_notes=("Premium valuation.",),
        momentum_notes=("Positive trend.",),
        portfolio_notes=("Largest holding.",),
    )

    assert context_builder.calls == [
        {
            "position": position,
            "market": market,
            "news": news,
            "valuation": None,
            "knowledge_base": knowledge_base,
            "relevant_research": (),
            "risk_notes": ("Sizing risk.",),
            "valuation_notes": ("Premium valuation.",),
            "momentum_notes": ("Positive trend.",),
            "portfolio_notes": ("Largest holding.",),
        }
    ]
    assert review_runner.calls == [consensus_builder.calls[0]["context"]]
    assert consensus_builder.calls[0]["reviews"][0].agent_name == "Dongdong"  # type: ignore[index,union-attr]
    assert decision is consensus_builder.decision


def test_workflow_returns_position_decision() -> None:
    service = PositionDecisionWorkflowService(
        context_builder=FakeContextBuilder(),  # type: ignore[arg-type]
        review_runner=FakeReviewRunner(),  # type: ignore[arg-type]
        consensus_builder=FakeConsensusBuilder(),  # type: ignore[arg-type]
    )

    decision = service(_position())

    assert isinstance(decision, PositionDecision)
    assert decision.symbol == "NVDA"


def test_workflow_preserves_one_position_boundary() -> None:
    context_builder = FakeContextBuilder()
    service = PositionDecisionWorkflowService(
        context_builder=context_builder,  # type: ignore[arg-type]
        review_runner=FakeReviewRunner(),  # type: ignore[arg-type]
        consensus_builder=FakeConsensusBuilder(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="exactly one position"):
        service.run((_position(), _position()))

    assert context_builder.calls == []


def test_workflow_rejects_portfolio_snapshot_like_inputs() -> None:
    context_builder = FakeContextBuilder()
    service = PositionDecisionWorkflowService(
        context_builder=context_builder,  # type: ignore[arg-type]
        review_runner=FakeReviewRunner(),  # type: ignore[arg-type]
        consensus_builder=FakeConsensusBuilder(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="exactly one position"):
        service.run({"positions": (_position(),)})

    assert context_builder.calls == []


def test_workflow_dependencies_can_be_replaced_with_fakes() -> None:
    context_builder = FakeContextBuilder()
    review_runner = FakeReviewRunner()
    consensus_builder = FakeConsensusBuilder(decision=_decision(symbol="AMD"))

    decision = PositionDecisionWorkflowService(
        context_builder=context_builder,  # type: ignore[arg-type]
        review_runner=review_runner,  # type: ignore[arg-type]
        consensus_builder=consensus_builder,  # type: ignore[arg-type]
    ).run(_position())

    assert decision.symbol == "AMD"
    assert len(context_builder.calls) == 1
    assert len(review_runner.calls) == 1
    assert len(consensus_builder.calls) == 1


def test_workflow_does_not_call_providers_directly() -> None:
    source = _workflow_source().lower()

    provider_terms = (
        "provider",
        "registry",
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "robinhood",
        "yahoo",
    )
    assert all(term not in source for term in provider_terms)


def test_workflow_does_not_generate_morning_report() -> None:
    source = _workflow_source().lower()

    assert "morning" not in source
    assert "daily" not in source
    assert "report" not in source
    assert "composer" not in source
    assert "render" not in source


def test_workflow_does_not_depend_on_gmail_scheduler_or_cli() -> None:
    source = _workflow_source().lower()

    assert "gmail" not in source
    assert "email" not in source
    assert "scheduler" not in source
    assert "launchd" not in source
    assert "cli" not in source


def _position() -> ProviderNeutralPosition:
    return ProviderNeutralPosition(
        symbol="NVDA",
        name="NVIDIA Corporation",
        quantity=2,
        market_value=1840,
        weight=0.25,
    )


def _review(
    agent_name: str,
    recommendation: PositionRecommendation,
) -> CommitteePositionReview:
    return CommitteePositionReview(
        symbol="NVDA",
        agent_name=agent_name,
        thesis=f"{agent_name} thesis.",
        concerns=(f"{agent_name} concern.",),
        recommendation=recommendation,
        confidence=ConfidenceLevel.MEDIUM,
        evidence_refs=(f"{agent_name} evidence.",),
    )


def _decision(symbol: str = "NVDA") -> PositionDecision:
    return PositionDecision(
        symbol=symbol,
        company_name="NVIDIA Corporation",
        recommendation=PositionRecommendation.WATCH,
        action_required=False,
        urgency=DecisionUrgency.LOW,
        final_rationale="Committee recommends watching the position.",
        dongdong_opinion="Opportunity remains attractive.",
        xixi_opinion="Fundamentals remain strong.",
        youyou_opinion="Sizing risk requires monitoring.",
        factual_evidence=("Committee reviewed supplied context.",),
        risks=("Monitor valuation risk.",),
        confidence=ConfidenceLevel.MEDIUM,
        human_review_required=False,
    )


def _workflow_source() -> str:
    return Path(
        "src/parakeetnest/services/position_decision_workflow.py"
    ).read_text(encoding="utf-8")
