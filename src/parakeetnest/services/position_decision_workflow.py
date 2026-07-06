"""Application workflow for one position-level investment decision."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from parakeetnest.context.models import (
    KnowledgeBaseSnapshot,
    MarketSnapshot,
    NewsContext,
    ValuationContextSnapshot,
)
from parakeetnest.models import PositionDecision
from parakeetnest.services.position_committee_review import (
    PositionCommitteeReviewRunner,
)
from parakeetnest.services.position_consensus import PositionConsensusBuilder
from parakeetnest.services.position_context import PositionContextBuilder


@dataclass(frozen=True)
class PositionDecisionWorkflowService:
    """Coordinate context, committee review, and consensus for one position."""

    context_builder: PositionContextBuilder
    review_runner: PositionCommitteeReviewRunner
    consensus_builder: PositionConsensusBuilder

    def run(
        self,
        position: object,
        *,
        market: MarketSnapshot | None = None,
        news: NewsContext | None = None,
        valuation: ValuationContextSnapshot | None = None,
        knowledge_base: KnowledgeBaseSnapshot | None = None,
        relevant_research: Iterable[str] = (),
        risk_notes: Iterable[str] = (),
        valuation_notes: Iterable[str] = (),
        momentum_notes: Iterable[str] = (),
        portfolio_notes: Iterable[str] = (),
    ) -> PositionDecision:
        """Return one PositionDecision from already-available inputs."""
        _validate_single_position(position)
        context = self.context_builder.build(
            position,
            market=market,
            news=news,
            valuation=valuation,
            knowledge_base=knowledge_base,
            relevant_research=relevant_research,
            risk_notes=risk_notes,
            valuation_notes=valuation_notes,
            momentum_notes=momentum_notes,
            portfolio_notes=portfolio_notes,
        )
        reviews = self.review_runner.run(context)
        return self.consensus_builder.build(context, reviews)

    def __call__(
        self,
        position: object,
        *,
        market: MarketSnapshot | None = None,
        news: NewsContext | None = None,
        valuation: ValuationContextSnapshot | None = None,
        knowledge_base: KnowledgeBaseSnapshot | None = None,
        relevant_research: Iterable[str] = (),
        risk_notes: Iterable[str] = (),
        valuation_notes: Iterable[str] = (),
        momentum_notes: Iterable[str] = (),
        portfolio_notes: Iterable[str] = (),
    ) -> PositionDecision:
        """Allow the workflow to be injected anywhere a callable is expected."""
        return self.run(
            position,
            market=market,
            news=news,
            valuation=valuation,
            knowledge_base=knowledge_base,
            relevant_research=relevant_research,
            risk_notes=risk_notes,
            valuation_notes=valuation_notes,
            momentum_notes=momentum_notes,
            portfolio_notes=portfolio_notes,
        )


def _validate_single_position(position: object) -> None:
    if isinstance(position, list | tuple | set | frozenset):
        raise ValueError("PositionDecisionWorkflowService accepts exactly one position")
    if isinstance(position, dict) and (
        "positions" in position or "top_holdings" in position
    ):
        raise ValueError("PositionDecisionWorkflowService accepts exactly one position")
    if hasattr(position, "positions") or hasattr(position, "top_holdings"):
        raise ValueError("PositionDecisionWorkflowService accepts exactly one position")


__all__ = ["PositionDecisionWorkflowService"]
