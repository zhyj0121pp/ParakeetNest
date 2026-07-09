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
        *,
        language: object | None = None,
    ) -> ResearchCommitteeConsensus:
        """Build the final advisory committee consensus."""
        from parakeetnest.research.models import ResearchCommitteeConsensus

        action = _committee_final_action(ticker_reports)
        confidence = _committee_confidence(ticker_reports)
        horizon = "3-6 months" if confidence != "low" else "next research update"
        risk_posture = _committee_risk_posture(ticker_reports)
        if _language_is_zh(language):
            horizon = "3-6 个月" if confidence != "low" else "下次研究更新"
            risk_posture = _committee_risk_posture_zh(ticker_reports)
            rationale = (
                "委员会在复核事实背景后形成本次建议，覆盖 "
                f"{len(ticker_reports)} 个标的："
                f"{_committee_action_mix(ticker_reports, language=language)}。"
            )
        else:
            rationale = (
                "The committee owns this advisory judgment after reviewing factual "
                f"context across {len(ticker_reports)} ticker(s): "
                f"{_committee_action_mix(ticker_reports)}."
            )
        return ResearchCommitteeConsensus(
            final_action=action,
            confidence=confidence,
            horizon=horizon,
            rationale=rationale,
            final_risk_posture=risk_posture,
            todays_suggested_actions=_todays_suggested_actions(
                ticker_reports,
                language=language,
            ),
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
    action_summary = _committee_action_mix(
        ticker_reports,
        language=context.report_language,
    )
    confidence_summary = _committee_confidence(ticker_reports)
    catalyst_summary = _summarize_context_values(context.upcoming_catalysts)
    risk_summary = _summarize_context_values(context.key_risks)
    evidence_summary = _summarize_context_values(context.ticker_summaries)
    missing_growth = _missing_growth_evidence(context)
    missing_fundamentals = _missing_fundamental_evidence(context)
    missing_risk = _missing_risk_evidence(context)

    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        if _context_is_zh(context):
            return (
                f"{tickers}: 上行空间只看可验证增长、催化剂和机会窗口。"
                f"当前行动观点为 {action_summary}，信心为 {confidence_summary}；"
                f"催化剂证据：{catalyst_summary}。"
                f"缺口：{missing_growth}。"
            )
        return (
            f"{tickers}: upside depends on verifiable growth, catalysts, and "
            f"opportunity windows. Current action view is {action_summary} with "
            f"{confidence_summary} confidence; catalyst evidence: "
            f"{catalyst_summary}. Missing growth evidence: {missing_growth}."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        if _context_is_zh(context):
            return (
                f"{tickers}: 资本保护优先，重点看下行、仓位大小和风险预算。"
                f"报告支持 {action_summary}，信心为 {confidence_summary}；"
                f"主要下行证据：{risk_summary}。缺口：{missing_risk}。"
            )
        return (
            f"{tickers}: capital preservation comes first, with attention to "
            f"downside, position sizing, and risk budget. The report supports "
            f"{action_summary} with {confidence_summary} confidence. Primary "
            f"downside evidence: {risk_summary}. Missing risk evidence: "
            f"{missing_risk}."
        )
    if _context_is_zh(context):
        return (
            f"{tickers}: 基本面、估值和执行质量需要先验证 "
            f"{action_summary} 行动观点。证据基础：{evidence_summary}。"
            f"缺口：{missing_fundamentals}。"
        )
    return (
        f"{tickers}: fundamentals, valuation, and execution quality should "
        f"validate the {action_summary} action view before risk is added. "
        f"Evidence base: {evidence_summary}. Missing fundamental evidence: "
        f"{missing_fundamentals}."
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
    if _context_is_zh(context):
        return _unique(values)[:4] or ("已连接的报告背景有限。",)
    return _unique(values)[:4] or ("Connected report context is limited.",)


def _committee_concern(context: CommitteePromptContext) -> str:
    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        if _context_is_zh(context):
            if context.upcoming_catalysts:
                return "催化剂仍需要证据证明上行空间不是单纯叙事驱动。"
            return "在出现更清晰的催化剂或创新信号前，上行案例仍偏弱。"
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
        if _context_is_zh(context):
            return _summarize_context_values(
                context.key_risks,
                limit=1,
            ) or "在已连接背景有限时，下行风险难以充分量化。"
        return _summarize_context_values(
            context.key_risks,
            limit=1,
        ) or "Downside risk cannot be sized well with limited connected context."
    if _context_is_zh(context):
        if context.evidence_notes:
            return "缺少已连接研究输入时，基本面信心仍然有限。"
        return "估值、盈利质量和执行证据需要继续复核。"
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
    actions = _committee_action_mix(
        ticker_reports,
        language=context.report_language,
    )
    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        if _context_is_zh(context):
            return (
                f"将 {actions} 作为复核建议，并在提高暴露前优先跟进催化剂证据。"
            )
        return (
            f"Treat {actions} as advisory guidance and prioritize catalyst follow-up "
            "before upgrading exposure."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        if _context_is_zh(context):
            return (
                f"将 {actions} 仅作为建议；保留现金灵活性，避免在风险证据不足时加大仓位。"
            )
        return (
            f"Treat {actions} as advisory only; preserve cash flexibility and avoid "
            "adding size without stronger risk evidence."
        )
    if _context_is_zh(context):
        return (
            f"将 {actions} 作为当前工作建议，并在任何人工决策前确认估值、盈利质量和执行证据。"
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
    if _context_is_zh(context):
        return (
            f"{tickers}: {context.persona.default_viewpoint} "
            f"证据：{evidence_summary}。"
            f"风险：{risk_summary}。"
            f"催化剂：{catalyst_summary}。"
        )
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


def _missing_growth_evidence(context: CommitteePromptContext) -> str:
    if any(
        "add thesis" not in catalyst.lower()
        for catalyst in context.upcoming_catalysts
    ):
        return "none obvious from the connected catalyst set"
    if _context_is_zh(context):
        return "缺少可验证增长催化剂、上行幅度和时间表"
    return "verifiable growth catalysts, upside magnitude, and timing"


def _missing_fundamental_evidence(context: CommitteePromptContext) -> str:
    if context.ticker_summaries and not context.evidence_notes:
        return "none obvious from the connected ticker summaries"
    if _context_is_zh(context):
        return "缺少估值、盈利质量、管理层执行和财务趋势输入"
    return (
        "valuation, earnings quality, management execution, and financial "
        "trend inputs"
    )


def _missing_risk_evidence(context: CommitteePromptContext) -> str:
    if (
        context.key_risks
        and "No portfolio service is connected" not in context.portfolio_review
    ):
        return "none obvious from connected risks and portfolio context"
    if _context_is_zh(context):
        return "缺少下行情景、仓位大小、集中度和组合风险预算输入"
    return (
        "downside scenarios, position size, concentration, and portfolio risk "
        "budget inputs"
    )


def _todays_suggested_actions(
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    language: object | None = None,
) -> tuple[str, ...]:
    return tuple(_committee_ticker_actions(ticker_reports, language=language))


def _committee_ticker_actions(
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    language: object | None = None,
) -> tuple[str, ...]:
    confidence = _committee_confidence(ticker_reports)
    horizon = "3-6 months" if confidence != "low" else "next research update"
    if _language_is_zh(language):
        horizon = "3-6 个月" if confidence != "low" else "下次研究更新"
        confidence_label = _level_label(confidence, language=language)
        return tuple(
            f"{ticker_report.ticker}: "
            f"{_action_label(_committee_action(ticker_report), language=language)} "
            f"（信心：{confidence_label}）周期：{horizon}；由你最终决定。"
            for ticker_report in ticker_reports
        )
    return tuple(
        f"{ticker_report.ticker}: {_committee_action(ticker_report).upper()} "
        f"({confidence} confidence) over {horizon}; human investor decides."
        for ticker_report in ticker_reports
    )


def _committee_action_mix(
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    language: object | None = None,
) -> str:
    counts: dict[str, int] = {}
    for ticker_report in ticker_reports:
        action = _action_label(_committee_action(ticker_report), language=language)
        counts[action] = counts.get(action, 0) + 1
    return ", ".join(
        f"{action}: {count}" for action, count in sorted(counts.items())
    ) or ("暂无委员会行动" if _language_is_zh(language) else "no committee actions")


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


def _committee_risk_posture_zh(
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> str:
    if _has_elevated_risk(ticker_reports):
        return "谨慎；事实风险信号偏高，增加暴露前需要人工复核。"
    if _committee_confidence(ticker_reports) == "low":
        return "谨慎；已连接证据有限，本报告仅作复核建议。"
    return "均衡；证据足以支持复核，但不足以支持自动行动。"


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


def _context_is_zh(context: CommitteePromptContext) -> bool:
    return _language_is_zh(context.report_language)


def _language_is_zh(language: object | None) -> bool:
    if language is None:
        return False
    raw_value = getattr(language, "value", language)
    return str(raw_value).strip().lower() == "zh"


def _action_label(action: str, *, language: object | None = None) -> str:
    if not _language_is_zh(language):
        return action.upper()
    return {
        "buy": "买入复核",
        "add": "加仓复核",
        "buy_more": "加仓复核",
        "hold": "继续持有",
        "watch": "继续观察",
        "trim": "减仓复核",
        "reduce": "减仓复核",
        "sell": "卖出复核",
    }.get(action.strip().lower(), action)


def _level_label(value: str, *, language: object | None = None) -> str:
    if not _language_is_zh(language):
        return value
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(value.strip().lower(), value)


__all__ = ["CommitteeJudgmentService"]
