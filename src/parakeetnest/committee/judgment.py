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
        _is_substantive_catalyst(catalyst.summary)
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
    evidence_summary = _summarize_context_values(
        context.company_facts
        + context.public_market_facts
        + context.profile_facts
        + context.valuation_facts
        + context.news_facts
        + context.ticker_summaries
    )
    interpretation_summary = _ticker_interpretation_summary(ticker_reports)
    macro_summary = _summarize_context_values(context.macro_facts)
    position_summary = _position_context_summary(context)
    portfolio_summary = _portfolio_summary_text(context)
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
                f"委员会前分析：{interpretation_summary}。"
                f"组合约束：{position_summary}。"
                f"缺口：{missing_growth}。"
            )
        return (
            f"{tickers}: upside depends on verifiable growth, catalysts, and "
            f"opportunity windows. Current action view is {action_summary} with "
            f"{confidence_summary} confidence; catalyst evidence: "
            f"{catalyst_summary}. Pre-committee analysis: {interpretation_summary}. "
            f"Portfolio add constraint: {position_summary}. "
            f"Missing growth evidence: {missing_growth}."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        if _context_is_zh(context):
            return (
                f"{tickers}: 资本保护优先，重点看下行、仓位大小和风险预算。"
                f"报告支持 {action_summary}，信心为 {confidence_summary}；"
                f"主要下行证据：{risk_summary}。宏观：{macro_summary}。"
                f"委员会前分析：{interpretation_summary}。"
                f"组合风险：{portfolio_summary}; {position_summary}。"
                f"缺口：{missing_risk}。"
            )
        return (
            f"{tickers}: capital preservation comes first, with attention to "
            f"downside, position sizing, and risk budget. The report supports "
            f"{action_summary} with {confidence_summary} confidence. Primary "
            f"downside evidence: {risk_summary}. Macro facts: {macro_summary}. "
            f"Pre-committee analysis: {interpretation_summary}. "
            f"Portfolio risk context: {portfolio_summary}; {position_summary}. "
            f"Missing risk evidence: {missing_risk}."
        )
    if _context_is_zh(context):
        return (
            f"{tickers}: 基本面、估值和执行质量需要先验证 "
            f"{action_summary} 行动观点。证据基础：{evidence_summary}。"
            f"委员会前分析：{interpretation_summary}。"
            f"当前持仓角色：{position_summary}。"
            f"缺口：{missing_fundamentals}。"
        )
    return (
        f"{tickers}: fundamentals, valuation, and execution quality should "
        f"validate the {action_summary} action view before risk is added. "
        f"Evidence base: {evidence_summary}. Current exposure: "
        f"{position_summary}. Pre-committee analysis: {interpretation_summary}. "
        f"Missing fundamental evidence: {missing_fundamentals}."
    )


def _committee_evidence(context: CommitteePromptContext) -> tuple[str, ...]:
    role = context.persona.role
    if role is CommitteeRole.CHIEF_GROWTH_OFFICER:
        values = (
            context.upcoming_catalysts
            + context.public_market_facts
            + context.profile_facts
            + context.valuation_facts
            + context.news_facts
            + context.ticker_summaries
        )
    elif role is CommitteeRole.CHIEF_RISK_OFFICER:
        values = (
            context.key_risks
            + context.macro_facts
            + (context.market_summary, context.portfolio_review)
            + context.evidence_notes
        )
    else:
        values = (
            context.company_facts
            + context.public_market_facts
            + context.profile_facts
            + context.valuation_facts
            + context.news_facts
            + context.ticker_summaries
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
        if context.position_context is not None and not context.position_context.add_allowed:
            if _context_is_zh(context):
                return "组合桶位显示当前不宜加仓，除非新的公开增长证据显著改变判断。"
            return (
                "Bucketed portfolio context does not allow adding exposure "
                "without stronger public growth evidence."
            )
        if _context_is_zh(context):
            return (
                f"将 {actions} 作为复核建议，并在提高暴露前优先跟进催化剂证据。"
            )
        return (
            f"Treat {actions} as advisory guidance and prioritize catalyst follow-up "
            "before upgrading exposure."
        )
    if role is CommitteeRole.CHIEF_RISK_OFFICER:
        if context.position_context is not None and context.position_context.trim_candidate:
            if _context_is_zh(context):
                return f"将 {actions} 仅作为建议；桶位显示该持仓是减仓候选。"
            return (
                f"Treat {actions} as advisory only; bucketed portfolio context "
                "marks this holding as a trim candidate."
            )
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
    if any(_is_substantive_catalyst(catalyst) for catalyst in context.upcoming_catalysts):
        return "none obvious from the connected catalyst set"
    if _context_is_zh(context):
        return "缺少可验证增长催化剂、上行幅度和时间表"
    return "verifiable growth catalysts, upside magnitude, and timing"


def _is_substantive_catalyst(value: str) -> bool:
    normalized = value.lower().strip()
    return not (
        normalized.startswith("add thesis")
        or normalized.endswith("no connected factual context available.")
        or normalized == "no connected factual context available"
    )


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
    has_holding = (
        ticker_report.position_context.is_holding
        if ticker_report.position_context is not None
        else any(finding.source == "portfolio" for finding in ticker_report.findings)
    )
    if (
        ticker_report.position_context is not None
        and ticker_report.position_context.trim_candidate
    ):
        if ticker_report.fact_interpretation.valuation_label in {
            "expensive",
            "extreme",
            "revenue_multiple_risk",
        }:
            return "reduce"
        if ticker_report.position_context.position_size_bucket == "very_large":
            return "reduce"
        return "hold"
    if (
        has_holding
        and ticker_report.fact_interpretation.valuation_label
        in {"extreme", "revenue_multiple_risk"}
        and _ticker_has_elevated_risk(ticker_report)
    ):
        return "reduce"
    if has_holding and _ticker_has_elevated_risk(ticker_report):
        return "hold"
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
    interpretation = ticker_report.fact_interpretation
    if interpretation.valuation_label in {"extreme", "revenue_multiple_risk"}:
        return True
    interpreted_risk = interpretation.risk_summary.lower()
    if "high beta" in interpreted_risk or "very_large position" in interpreted_risk:
        return True
    if (
        ticker_report.portfolio_summary is not None
        and ticker_report.portfolio_summary.concentration_level in {"high", "very_high"}
    ):
        return True
    return any(
        marker in risk_text
        for marker in ("high", "extreme", "severe", "concentration", "export controls")
    )


def _ticker_interpretation_summary(
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> str:
    summaries = []
    for ticker_report in ticker_reports:
        interpretation = ticker_report.fact_interpretation
        summaries.append(
            f"{ticker_report.ticker}: {interpretation.profile_summary}; "
            f"{interpretation.valuation_summary}; "
            f"{interpretation.risk_summary}; "
            f"{interpretation.catalyst_summary}"
        )
    return "; ".join(summaries) if summaries else "limited interpreted facts"


def _position_context_summary(context: CommitteePromptContext) -> str:
    position_context = context.position_context
    if position_context is None:
        return "no bucketed position context"
    return (
        f"holding_role={position_context.holding_role}, "
        f"position_size_bucket={position_context.position_size_bucket}, "
        f"rank_bucket={position_context.portfolio_rank_bucket}, "
        f"return_bucket={position_context.unrealized_return_bucket}, "
        f"add_allowed={position_context.add_allowed}, "
        f"trim_candidate={position_context.trim_candidate}"
    )


def _portfolio_summary_text(context: CommitteePromptContext) -> str:
    summary = context.portfolio_summary
    if summary is None:
        return "no bucketed portfolio summary"
    return (
        f"cash_bucket={summary.cash_allocation_bucket}, "
        f"concentration_level={summary.concentration_level}, "
        f"largest_position_bucket={summary.largest_position_bucket}, "
        f"top5_bucket={summary.top5_concentration_bucket}"
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
