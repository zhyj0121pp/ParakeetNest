"""Deterministic portfolio decision summary builder."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from parakeetnest.models import (
    ConfidenceLevel,
    DecisionUrgency,
    PortfolioDecisionSummary,
    PositionDecision,
)


_URGENCY_RANK = {
    DecisionUrgency.NONE: 0,
    DecisionUrgency.LOW: 1,
    DecisionUrgency.MEDIUM: 2,
    DecisionUrgency.HIGH: 3,
}
_CONFIDENCE_SCORE = {
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MEDIUM: 2,
    ConfidenceLevel.HIGH: 3,
}
_SCORE_CONFIDENCE = {
    1: ConfidenceLevel.LOW,
    2: ConfidenceLevel.MEDIUM,
    3: ConfidenceLevel.HIGH,
}


@dataclass(frozen=True)
class PortfolioDecisionSummaryBuilder:
    """Build a portfolio-level summary from completed position decisions."""

    def build(
        self,
        decisions: tuple[PositionDecision, ...],
        *,
        sector_exposure_notes: Iterable[str] = (),
        cash_allocation_notes: Iterable[str] = (),
        portfolio_notes: Iterable[str] = (),
    ) -> PortfolioDecisionSummary:
        """Return one deterministic PortfolioDecisionSummary for decisions."""
        action_required = tuple(
            decision for decision in decisions if decision.action_required
        )
        no_action = tuple(
            decision for decision in decisions if not decision.action_required
        )

        return PortfolioDecisionSummary(
            overall_portfolio_view=_overall_portfolio_view(
                action_required=action_required,
                no_action=no_action,
                decisions=decisions,
                portfolio_notes=portfolio_notes,
            ),
            concentration_risks=_concentration_risks(decisions),
            sector_exposure_notes=_clean_notes(sector_exposure_notes),
            cash_allocation_notes=_clean_notes(cash_allocation_notes),
            action_items=tuple(_action_item(decision) for decision in action_required),
            no_action_positions=tuple(decision.symbol for decision in no_action),
        )

    def __call__(
        self,
        decisions: tuple[PositionDecision, ...],
        *,
        sector_exposure_notes: Iterable[str] = (),
        cash_allocation_notes: Iterable[str] = (),
        portfolio_notes: Iterable[str] = (),
    ) -> PortfolioDecisionSummary:
        """Allow the builder to be injected anywhere a callable is expected."""
        return self.build(
            decisions,
            sector_exposure_notes=sector_exposure_notes,
            cash_allocation_notes=cash_allocation_notes,
            portfolio_notes=portfolio_notes,
        )


def _overall_portfolio_view(
    *,
    action_required: tuple[PositionDecision, ...],
    no_action: tuple[PositionDecision, ...],
    decisions: tuple[PositionDecision, ...],
    portfolio_notes: Iterable[str],
) -> str:
    highest_urgency = _highest_urgency(decisions)
    view = (
        f"{len(action_required)} action-required positions; "
        f"{len(no_action)} no-action positions; "
        f"highest urgency: {highest_urgency.value}"
    )
    confidence = _overall_confidence(decisions)
    if confidence is not None:
        view = f"{view}; overall confidence: {confidence.value}"
    notes = _clean_notes(portfolio_notes)
    if notes:
        view = f"{view}; portfolio context: {'; '.join(notes)}"
    return _sentence(view)


def _highest_urgency(decisions: tuple[PositionDecision, ...]) -> DecisionUrgency:
    if not decisions:
        return DecisionUrgency.NONE
    return max(
        (decision.urgency for decision in decisions),
        key=lambda urgency: _URGENCY_RANK[urgency],
    )


def _overall_confidence(
    decisions: tuple[PositionDecision, ...],
) -> ConfidenceLevel | None:
    if not decisions:
        return None
    average_score = round(
        sum(_CONFIDENCE_SCORE[decision.confidence] for decision in decisions)
        / len(decisions)
    )
    return _SCORE_CONFIDENCE[average_score]


def _concentration_risks(
    decisions: tuple[PositionDecision, ...],
) -> tuple[str, ...]:
    risks: list[str] = []
    for decision in decisions:
        if decision.urgency is not DecisionUrgency.HIGH:
            continue
        for risk in decision.risks:
            risks.append(f"{decision.symbol} high urgency: {risk}")
    return tuple(risks)


def _action_item(decision: PositionDecision) -> str:
    return (
        f"{decision.symbol}: {decision.recommendation.value} "
        f"({decision.urgency.value} urgency, {decision.confidence.value} confidence) - "
        f"{decision.final_rationale}"
    )


def _clean_notes(notes: Iterable[str]) -> tuple[str, ...]:
    return tuple(note.strip() for note in notes if note.strip())


def _sentence(text: str) -> str:
    if text.endswith((".", "!", "?")):
        return text
    return f"{text}."


__all__ = ["PortfolioDecisionSummaryBuilder"]
