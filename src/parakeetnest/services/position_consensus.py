"""Deterministic position consensus builder service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from parakeetnest.models import (
    CommitteePositionReview,
    ConfidenceLevel,
    DecisionUrgency,
    PositionContext,
    PositionDecision,
    PositionRecommendation,
)


_ACTION_RECOMMENDATIONS = frozenset(
    (
        PositionRecommendation.BUY_MORE,
        PositionRecommendation.TRIM,
        PositionRecommendation.SELL,
    )
)
_NO_ACTION_EQUIVALENTS = frozenset(
    (PositionRecommendation.HOLD, PositionRecommendation.NO_ACTION)
)
_RISK_OBJECTION_RECOMMENDATIONS = frozenset(
    (PositionRecommendation.TRIM, PositionRecommendation.SELL)
)
_RECOMMENDATION_PRIORITY = {
    PositionRecommendation.SELL: 5,
    PositionRecommendation.TRIM: 4,
    PositionRecommendation.BUY_MORE: 3,
    PositionRecommendation.WATCH: 2,
    PositionRecommendation.HOLD: 1,
    PositionRecommendation.NO_ACTION: 0,
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
class PositionConsensusBuilder:
    """Convert committee position reviews into one advisory position decision."""

    def build(
        self,
        context: PositionContext,
        reviews: tuple[CommitteePositionReview, ...],
    ) -> PositionDecision:
        """Return one deterministic PositionDecision from context and reviews."""
        if len(reviews) != 3:
            raise ValueError("exactly three committee reviews are required")
        _validate_review_symbols(context, reviews)

        recommendation = _consensus_recommendation(context, reviews)
        action_required = recommendation in _ACTION_RECOMMENDATIONS
        urgency = _urgency_for(recommendation, reviews)
        if recommendation is PositionRecommendation.NO_ACTION:
            action_required = False
            urgency = DecisionUrgency.NONE

        return PositionDecision(
            symbol=context.symbol,
            company_name=context.company_name,
            recommendation=recommendation,
            action_required=action_required,
            urgency=urgency,
            final_rationale=_final_rationale(context, recommendation, reviews),
            dongdong_opinion=_opinion_for("dongdong", reviews),
            xixi_opinion=_opinion_for("xixi", reviews),
            yoyo_opinion=_opinion_for("yoyo", reviews),
            factual_evidence=_factual_evidence(context, reviews),
            risks=_risks(context, reviews),
            confidence=_confidence_for(reviews),
            human_review_required=recommendation in _ACTION_RECOMMENDATIONS,
        )

    def __call__(
        self,
        context: PositionContext,
        reviews: tuple[CommitteePositionReview, ...],
    ) -> PositionDecision:
        """Allow the builder to be injected anywhere a callable is expected."""
        return self.build(context, reviews)


def _validate_review_symbols(
    context: PositionContext,
    reviews: tuple[CommitteePositionReview, ...],
) -> None:
    for review in reviews:
        if review.symbol != context.symbol:
            raise ValueError("committee review symbol must match position context")


def _consensus_recommendation(
    context: PositionContext,
    reviews: tuple[CommitteePositionReview, ...],
) -> PositionRecommendation:
    recommendations = tuple(review.recommendation for review in reviews)
    if all(recommendation in _NO_ACTION_EQUIVALENTS for recommendation in recommendations):
        if context.risk_notes:
            return PositionRecommendation.WATCH
        return PositionRecommendation.NO_ACTION

    counts = Counter(recommendations)
    highest_count = max(counts.values())
    tied = [
        recommendation
        for recommendation, count in counts.items()
        if count == highest_count
    ]
    return max(tied, key=lambda recommendation: _RECOMMENDATION_PRIORITY[recommendation])


def _urgency_for(
    recommendation: PositionRecommendation,
    reviews: tuple[CommitteePositionReview, ...],
) -> DecisionUrgency:
    yoyo = _review_for("yoyo", reviews)
    yoyo_risk_objection = (
        yoyo is not None and yoyo.recommendation in _RISK_OBJECTION_RECOMMENDATIONS
    )
    if recommendation is PositionRecommendation.SELL or (
        recommendation is PositionRecommendation.TRIM and yoyo_risk_objection
    ):
        return DecisionUrgency.HIGH
    if recommendation in _ACTION_RECOMMENDATIONS:
        return DecisionUrgency.MEDIUM if yoyo_risk_objection else DecisionUrgency.LOW
    if recommendation is PositionRecommendation.WATCH:
        return DecisionUrgency.MEDIUM if yoyo_risk_objection else DecisionUrgency.LOW
    return DecisionUrgency.LOW


def _confidence_for(reviews: tuple[CommitteePositionReview, ...]) -> ConfidenceLevel:
    average_score = round(
        sum(_CONFIDENCE_SCORE[review.confidence] for review in reviews) / len(reviews)
    )
    disagreement_penalty = len({review.recommendation for review in reviews}) - 1
    score = max(1, average_score - disagreement_penalty)
    return _SCORE_CONFIDENCE[score]


def _final_rationale(
    context: PositionContext,
    recommendation: PositionRecommendation,
    reviews: tuple[CommitteePositionReview, ...],
) -> str:
    recommendation_label = recommendation.value.replace("_", " ").upper()
    review_summary = "; ".join(
        f"{review.agent_name}: {review.recommendation.value}"
        for review in reviews
    )
    if recommendation is PositionRecommendation.NO_ACTION:
        return (
            f"{context.symbol} consensus is {recommendation_label}: "
            "committee views do not require a portfolio action today. "
            f"Inputs reviewed: {review_summary}."
        )
    return (
        f"{context.symbol} consensus is {recommendation_label} on an advisory basis. "
        f"Inputs reviewed: {review_summary}."
    )


def _opinion_for(agent_key: str, reviews: tuple[CommitteePositionReview, ...]) -> str:
    review = _review_for(agent_key, reviews)
    if review is None:
        return f"{agent_key.title()} did not provide a review."
    concerns = "; ".join(review.concerns) if review.concerns else "No stated concerns."
    return (
        f"{review.thesis} Recommendation: {review.recommendation.value}. "
        f"Confidence: {review.confidence.value}. Concerns: {concerns}"
    )


def _review_for(
    agent_key: str,
    reviews: tuple[CommitteePositionReview, ...],
) -> CommitteePositionReview | None:
    normalized_key = agent_key.lower()
    aliases = (normalized_key,)
    for review in reviews:
        normalized_name = review.agent_name.strip().lower()
        if any(alias in normalized_name for alias in aliases):
            return review
    return None


def _factual_evidence(
    context: PositionContext,
    reviews: tuple[CommitteePositionReview, ...],
) -> tuple[str, ...]:
    evidence = (
        *context.relevant_news,
        *context.relevant_research,
        *context.valuation_notes,
        *context.momentum_notes,
        *context.portfolio_notes,
        *(evidence_ref for review in reviews for evidence_ref in review.evidence_refs),
    )
    return _unique_text(evidence) or ("Committee reviewed current position context.",)


def _risks(
    context: PositionContext,
    reviews: tuple[CommitteePositionReview, ...],
) -> tuple[str, ...]:
    risks = (
        *context.risk_notes,
        *(concern for review in reviews for concern in review.concerns),
    )
    return _unique_text(risks) or ("Monitor for new material risk signals.",)


def _unique_text(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        text = value.strip()
        key = text.lower()
        if text and key not in seen:
            normalized.append(text)
            seen.add(key)
    return tuple(normalized)


__all__ = ["PositionConsensusBuilder"]
