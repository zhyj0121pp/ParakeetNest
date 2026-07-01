"""Deterministic committee-owned investment judgment helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from parakeetnest.committee.personas import CommitteeRole
from parakeetnest.committee.prompting import (
    CommitteePersonaPrompt,
    CommitteePromptContext,
)

if TYPE_CHECKING:
    from parakeetnest.research.models import (
        ResearchCommitteeConsensus,
        ResearchCommitteeOpinion,
        ResearchTickerReport,
    )


class CommitteeJudgmentService:
    """Produce committee opinions and consensus from factual ticker context."""

    def build_opinions(
        self,
        committee_prompts: tuple[CommitteePersonaPrompt, ...],
        ticker_reports: tuple[ResearchTickerReport, ...],
    ) -> tuple[ResearchCommitteeOpinion, ...]:
        """Build deterministic persona opinions for the daily report."""
        from parakeetnest.research.models import ResearchCommitteeOpinion

        return tuple(
            ResearchCommitteeOpinion(
                persona_id=prompt.persona_id,
                display_name=prompt.display_name,
                role_title=prompt.role_title,
                stance=_committee_stance(prompt.context, ticker_reports),
                reasoning_summary=_committee_reasoning(prompt.context, ticker_reports),
                evidence_considered=_committee_evidence(prompt.context),
                key_concern=_committee_concern(prompt.context),
                suggested_action=_committee_suggested_action(
                    prompt.context,
                    ticker_reports,
                ),
                responsibility=prompt.context.persona.responsibility,
                viewpoint=_committee_viewpoint(prompt.context),
                risk_posture=prompt.context.persona.risk_posture,
                evidence_requirements=prompt.context.persona.evidence_requirements,
                writing_style=prompt.context.persona.writing_style.value,
                decision_biases_to_avoid=(
                    prompt.context.persona.decision_biases_to_avoid
                ),
            )
            for prompt in committee_prompts
        )

    def build_consensus(
        self,
        ticker_reports: tuple[ResearchTickerReport, ...],
    ) -> ResearchCommitteeConsensus:
        """Build the final advisory committee consensus."""
        from parakeetnest.research.models import ResearchCommitteeConsensus

        action = _committee_final_action(ticker_reports)
        confidence = _committee_confidence(ticker_reports)
        horizon = "3-6 months" if confidence != "low" else "next research update"
        risk_posture = _committee_risk_posture(ticker_reports)
        return ResearchCommitteeConsensus(
            final_action=action,
            confidence=confidence,
            horizon=horizon,
            rationale=(
                "The committee owns this advisory judgment after reviewing factual "
                f"context across {len(ticker_reports)} ticker(s): "
                f"{_committee_action_mix(ticker_reports)}."
            ),
            final_risk_posture=risk_posture,
            todays_suggested_actions=_todays_suggested_actions(ticker_reports),
        )


def _committee_stance(
    context: CommitteePromptContext,
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> str:
    elevated_risk = _has_elevated_risk(ticker_reports)
    limited_context = _committee_confidence(ticker_reports) == "low"
    has_substantive_catalysts = any(
        not catalyst.summary.lower().startswith("add thesis")
        for ticker_report in ticker_reports
        for catalyst in ticker_report.catalysts
    )
    has_holdings = any(
        any(finding.source == "portfolio" for finding in ticker_report.findings)
        for ticker_report in ticker_reports
    )

    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        if elevated_risk:
            return "neutral"
        if limited_context and not has_substantive_catalysts:
            return "neutral"
        return "bullish" if has_substantive_catalysts else "neutral"
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        if elevated_risk or limited_context or context.key_risks:
            return "cautious"
        return "neutral"
    if elevated_risk:
        return "cautious"
    return "neutral" if limited_context or not has_holdings else "bullish"


def _committee_reasoning(
    context: CommitteePromptContext,
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> str:
    tickers = ", ".join(context.tickers)
    action_summary = _committee_action_mix(ticker_reports)
    confidence_summary = _committee_confidence(ticker_reports)
    catalyst_summary = _summarize_context_values(context.upcoming_catalysts)
    risk_summary = _summarize_context_values(context.key_risks)

    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        return (
            f"{tickers}: upside depends on identifiable catalysts and durable "
            f"growth evidence. Committee action view is {action_summary} with "
            f"{confidence_summary} confidence; catalyst evidence: {catalyst_summary}."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        return (
            f"{tickers}: capital preservation comes first while the report "
            f"supports {action_summary} with {confidence_summary} confidence. "
            f"Primary downside evidence: {risk_summary}."
        )
    return (
        f"{tickers}: fundamentals and execution evidence should validate the "
        f"committee's {action_summary} action view before risk is added. "
        f"Evidence base: {_summarize_context_values(context.ticker_summaries)}."
    )


def _committee_evidence(context: CommitteePromptContext) -> tuple[str, ...]:
    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        values = context.upcoming_catalysts + context.ticker_summaries
    elif role is CommitteeRole.CHIEF_RISK_OFFICER:
        values = (
            context.key_risks
            + (context.market_summary, context.portfolio_review)
            + context.evidence_notes
        )
    else:
        values = (
            context.ticker_summaries
            + (context.portfolio_review, context.watchlist_review)
            + context.evidence_notes
        )
    return _unique(values)[:4] or ("Connected report context is limited.",)


def _committee_concern(context: CommitteePromptContext) -> str:
    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        if context.upcoming_catalysts:
            return (
                "Catalysts still need evidence that upside is not purely "
                "narrative-driven."
            )
        return (
            "Upside case is weak until clearer catalysts or innovation signals "
            "are added."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        return _summarize_context_values(
            context.key_risks,
            limit=1,
        ) or "Downside risk cannot be sized well with limited connected context."
    if context.evidence_notes:
        return (
            "Fundamental conviction remains limited by missing connected "
            "research inputs."
        )
    return "Valuation, earnings quality, and execution evidence need continued review."


def _committee_suggested_action(
    context: CommitteePromptContext,
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> str:
    actions = _committee_action_mix(ticker_reports)
    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        return (
            f"Treat {actions} as advisory guidance and prioritize catalyst follow-up "
            "before upgrading exposure."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        return (
            f"Treat {actions} as advisory only; preserve cash flexibility and avoid "
            "adding size without stronger risk evidence."
        )
    return (
        f"Use {actions} as the working advisory plan, then confirm valuation, "
        "earnings quality, and execution evidence before any human decision."
    )


def _committee_viewpoint(context: CommitteePromptContext) -> str:
    tickers = ", ".join(context.tickers)
    evidence_summary = _summarize_context_values(context.evidence_notes)
    risk_summary = _summarize_context_values(context.key_risks)
    catalyst_summary = _summarize_context_values(context.upcoming_catalysts)
    return (
        f"{tickers}: {context.persona.default_viewpoint} "
        f"Evidence: {evidence_summary}. "
        f"Risks: {risk_summary}. "
        f"Catalysts: {catalyst_summary}."
    )


def _summarize_context_values(values: tuple[str, ...], limit: int = 2) -> str:
    if not values:
        return "limited connected context"
    return "; ".join(values[:limit])


def _todays_suggested_actions(
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> tuple[str, ...]:
    return tuple(_committee_ticker_actions(ticker_reports))


def _committee_ticker_actions(
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> tuple[str, ...]:
    confidence = _committee_confidence(ticker_reports)
    horizon = "3-6 months" if confidence != "low" else "next research update"
    return tuple(
        f"{ticker_report.ticker}: {_committee_action(ticker_report).upper()} "
        f"({confidence} confidence) over {horizon}; human investor decides."
        for ticker_report in ticker_reports
    )


def _committee_action_mix(ticker_reports: tuple[ResearchTickerReport, ...]) -> str:
    counts: dict[str, int] = {}
    for ticker_report in ticker_reports:
        action = _committee_action(ticker_report).upper()
        counts[action] = counts.get(action, 0) + 1
    return ", ".join(
        f"{action}: {count}" for action, count in sorted(counts.items())
    ) or "no committee actions"


def _committee_action(ticker_report: ResearchTickerReport) -> str:
    has_holding = any(finding.source == "portfolio" for finding in ticker_report.findings)
    if has_holding and _ticker_has_elevated_risk(ticker_report):
        return "reduce"
    if has_holding:
        return "hold"
    return "watch"


def _committee_final_action(ticker_reports: tuple[ResearchTickerReport, ...]) -> str:
    actions = {_committee_action(ticker_report) for ticker_report in ticker_reports}
    if "sell" in actions:
        return "sell"
    if "reduce" in actions:
        return "reduce"
    if "hold" in actions:
        return "hold"
    return "watch"


def _committee_confidence(ticker_reports: tuple[ResearchTickerReport, ...]) -> str:
    if not ticker_reports:
        return "low"
    source_counts = [
        len({finding.source for finding in ticker_report.findings if finding.source})
        for ticker_report in ticker_reports
    ]
    if min(source_counts) >= 3:
        return "high"
    if min(source_counts) >= 2:
        return "medium"
    return "low"


def _committee_risk_posture(ticker_reports: tuple[ResearchTickerReport, ...]) -> str:
    if _has_elevated_risk(ticker_reports):
        return "Cautious; elevated factual risk signals require human review before adding exposure."
    if _committee_confidence(ticker_reports) == "low":
        return "Cautious; connected evidence is limited and the report is advisory only."
    return "Balanced; evidence is sufficient for review but not for autonomous action."


def _has_elevated_risk(ticker_reports: tuple[ResearchTickerReport, ...]) -> bool:
    return any(_ticker_has_elevated_risk(ticker_report) for ticker_report in ticker_reports)


def _ticker_has_elevated_risk(ticker_report: ResearchTickerReport) -> bool:
    risk_text = " ".join(risk.summary.lower() for risk in ticker_report.risks)
    return any(
        marker in risk_text
        for marker in ("high", "extreme", "severe", "concentration", "export controls")
    )


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


__all__ = ["CommitteeJudgmentService"]
