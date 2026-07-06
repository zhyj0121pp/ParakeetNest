"""Application workflow for position decisions across a portfolio."""

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
from parakeetnest.services.position_decision_workflow import (
    PositionDecisionWorkflowService,
)


@dataclass(frozen=True)
class PortfolioPositionDecisionWorkflowService:
    """Run the one-position decision workflow for each supplied holding."""

    position_decision_workflow: PositionDecisionWorkflowService

    def run(
        self,
        portfolio: object | Iterable[object],
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
    ) -> tuple[PositionDecision, ...]:
        """Return one PositionDecision per position in portfolio order."""
        positions = _positions_from(portfolio)
        return tuple(
            self.position_decision_workflow.run(
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
            for position in positions
        )

    def __call__(
        self,
        portfolio: object | Iterable[object],
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
    ) -> tuple[PositionDecision, ...]:
        """Allow the workflow to be injected anywhere a callable is expected."""
        return self.run(
            portfolio,
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


def _positions_from(portfolio: object | Iterable[object]) -> tuple[object, ...]:
    if isinstance(portfolio, dict):
        if "positions" in portfolio:
            return tuple(portfolio["positions"])
        if "holdings" in portfolio:
            return tuple(portfolio["holdings"])

    positions = getattr(portfolio, "positions", None)
    if positions is not None:
        return tuple(positions)

    holdings = getattr(portfolio, "holdings", None)
    if holdings is not None:
        return tuple(holdings)

    if isinstance(portfolio, Iterable):
        return tuple(portfolio)

    raise TypeError(
        "PortfolioPositionDecisionWorkflowService requires positions or holdings"
    )


__all__ = ["PortfolioPositionDecisionWorkflowService"]
