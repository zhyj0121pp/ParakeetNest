"""Localization support for reader-facing investment research reports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from parakeetnest.config import get_settings


class ReportLanguage(StrEnum):
    """Supported report output languages."""

    EN = "en"
    ZH = "zh"

    @classmethod
    def from_value(cls, value: "ReportLanguage | str | None") -> "ReportLanguage":
        """Normalize a configured report language value."""
        if value is None:
            return cls.EN
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError("report language must be en or zh") from exc


@dataclass(frozen=True)
class ReportLocalization:
    """Reader-facing labels and deterministic text for report rendering."""

    language: ReportLanguage
    report_title: str
    action_required: str
    position_cards: str
    stable_holdings: str
    new_opportunities: str
    market_overview: str
    raw_evidence: str
    recommendation: str
    confidence: str
    urgency: str
    rationale: str
    risks: str
    final_consensus: str
    dongdong: str
    xixi: str
    youyou: str
    factual_evidence: str
    show_stable_holdings: str
    show_raw_evidence: str
    committee_opinions_and_factual_evidence: str
    human_review_required: str
    no_automatic_action_review_recommended: str
    not_available: str
    no_available_info: str
    human_review_notice: str
    positions_requiring_review: str
    no_action_required_positions: str
    no_position_cards: str
    no_stable_holdings: str
    no_raw_evidence: str
    portfolio_action_item: str
    portfolio_context: str
    portfolio_view: str
    concentration_risk: str
    sector_exposure: str
    cash_allocation: str
    current_status: str
    suggested_action: str
    share_guidance: str
    target_weight: str
    execution_style: str
    action_and_sizing_review: str
    review_in_tranches_no_trade: str
    high_risk: str
    overweight: str
    position_needs_review: str
    share_count_manual_confirmation: str
    target_weight_manual_confirmation: str
    current_no_action: str
    sensitive_holding_data_hidden: str
    language_instruction: str
    position_language_instruction: str
    recommendation_labels: dict[str, str]
    level_labels: dict[str, str]

    def recommendation_label(self, value: object) -> str:
        """Return a localized recommendation label when known."""
        raw_value = getattr(value, "value", value)
        normalized = str(raw_value).strip().lower().replace(" ", "_")
        if normalized == "add":
            normalized = "buy_more"
        if normalized == "reduce":
            normalized = "trim"
        return self.recommendation_labels.get(normalized, _title_value(str(raw_value)))

    def level_label(self, value: object) -> str:
        """Return a localized confidence or urgency label when known."""
        raw_value = getattr(value, "value", value)
        normalized = str(raw_value).strip().lower().replace(" ", "_")
        return self.level_labels.get(normalized, _title_value(str(raw_value)))


EN_REPORT_LOCALIZATION = ReportLocalization(
    language=ReportLanguage.EN,
    report_title="Morning Investment Report",
    action_required="Action Required",
    position_cards="Position Cards",
    stable_holdings="Stable Holdings",
    new_opportunities="New Opportunities",
    market_overview="Market Overview",
    raw_evidence="Raw Evidence",
    recommendation="Recommendation",
    confidence="Confidence",
    urgency="Urgency",
    rationale="Rationale",
    risks="Risks",
    final_consensus="Final consensus",
    dongdong="Dongdong",
    xixi="Xixi",
    youyou="Youyou",
    factual_evidence="Factual evidence",
    show_stable_holdings="Show stable holdings",
    show_raw_evidence="Show raw evidence",
    committee_opinions_and_factual_evidence=(
        "Committee opinions and factual evidence"
    ),
    human_review_required="Human review required",
    no_automatic_action_review_recommended=(
        "No automatic action. User review recommended."
    ),
    not_available="Not available",
    no_available_info="No available information",
    human_review_notice=(
        "This report is advisory guidance only. It does not execute trades. "
        "Final decisions require human review."
    ),
    positions_requiring_review=(
        "Positions requiring user review or decision. This report is advisory "
        "guidance and does not take action for you."
    ),
    no_action_required_positions=(
        "No position decisions currently require user action."
    ),
    no_position_cards="No action-required position cards available.",
    no_stable_holdings="No stable holdings available.",
    no_raw_evidence="No raw evidence available.",
    portfolio_action_item="Portfolio action item",
    portfolio_context="Portfolio context",
    portfolio_view="Portfolio view",
    concentration_risk="Concentration risk",
    sector_exposure="Sector exposure",
    cash_allocation="Cash allocation",
    current_status="Current status",
    suggested_action="Suggested action",
    share_guidance="Reference shares",
    target_weight="Target weight",
    execution_style="Execution style",
    action_and_sizing_review="Action and sizing review",
    review_in_tranches_no_trade="Review in tranches; no automatic trade",
    high_risk="Elevated risk",
    overweight="Position overweight",
    position_needs_review="Position needs review",
    share_count_manual_confirmation="Specific share count requires manual confirmation.",
    target_weight_manual_confirmation="Specific target weight requires manual confirmation.",
    current_no_action="No action currently recommended.",
    sensitive_holding_data_hidden="Sensitive holding data hidden.",
    language_instruction=(
        "Write final report-facing content in English. Do not translate ticker "
        "symbols, company names, source names, or numeric values."
    ),
    position_language_instruction=(
        "Write thesis, concerns, and evidence_refs in English. Do not translate "
        "ticker symbols, company names, source names, or numeric values."
    ),
    recommendation_labels={
        "buy_more": "Add",
        "hold": "Hold",
        "watch": "Watch",
        "trim": "Trim",
        "sell": "Sell",
        "no_action": "Hold",
    },
    level_labels={
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "none": "None",
    },
)


ZH_REPORT_LOCALIZATION = ReportLocalization(
    language=ReportLanguage.ZH,
    report_title="早间投资报告",
    action_required="需要处理",
    position_cards="持仓决策卡片",
    stable_holdings="稳定持仓",
    new_opportunities="新机会",
    market_overview="市场概览",
    raw_evidence="原始证据",
    recommendation="建议",
    confidence="信心",
    urgency="紧急程度",
    rationale="理由",
    risks="风险",
    final_consensus="最终共识",
    dongdong="东东",
    xixi="西西",
    youyou="悠悠",
    factual_evidence="事实依据",
    show_stable_holdings="展开稳定持仓",
    show_raw_evidence="展开原始证据",
    committee_opinions_and_factual_evidence="委员会观点与事实依据",
    human_review_required="需要人工复核",
    no_automatic_action_review_recommended=(
        "不会自动执行交易，建议你人工复核。"
    ),
    not_available="暂无",
    no_available_info="暂无",
    human_review_notice=(
        "本报告仅提供投资分析与复核建议，不会自动执行任何交易。最终决策由你确认。"
    ),
    positions_requiring_review=(
        "以下持仓需要你复核或决策。本报告仅提供建议，不会替你执行操作。"
    ),
    no_action_required_positions="当前没有需要处理的持仓决策。",
    no_position_cards="暂无需要处理的持仓决策卡片。",
    no_stable_holdings="暂无稳定持仓信息。",
    no_raw_evidence="暂无原始证据。",
    portfolio_action_item="组合待办",
    portfolio_context="组合背景",
    portfolio_view="组合观点",
    concentration_risk="集中度风险",
    sector_exposure="行业暴露",
    cash_allocation="现金安排",
    current_status="当前状态",
    suggested_action="建议动作",
    share_guidance="参考股数",
    target_weight="目标仓位",
    execution_style="执行方式",
    action_and_sizing_review="行动与仓位复核",
    review_in_tranches_no_trade="建议分批复核，不自动交易",
    high_risk="风险偏高",
    overweight="仓位偏高",
    position_needs_review="仓位需要复核",
    share_count_manual_confirmation="具体股数需人工确认。",
    target_weight_manual_confirmation="具体比例需人工确认。",
    current_no_action="当前无需处理。",
    sensitive_holding_data_hidden="敏感持仓数据已隐藏。",
    language_instruction=(
        "请用中文撰写最终报告中面向读者展示的内容。不要翻译股票代码、公司名称、"
        "数据源名称或数字。"
    ),
    position_language_instruction=(
        "请用中文撰写 thesis、concerns 和 evidence_refs。不要翻译股票代码、公司名称、"
        "数据源名称或数字。"
    ),
    recommendation_labels={
        "buy_more": "加仓复核",
        "buy": "买入复核",
        "add": "加仓复核",
        "hold": "继续持有",
        "watch": "继续观察",
        "trim": "减仓复核",
        "reduce": "减仓复核",
        "sell": "卖出复核",
        "no_action": "继续持有",
    },
    level_labels={
        "high": "高",
        "medium": "中",
        "low": "低",
        "none": "无",
    },
)


def get_configured_report_language() -> ReportLanguage:
    """Return report language from environment-backed settings."""
    return ReportLanguage.from_value(get_settings().report_language)


def get_report_localization(
    language: ReportLanguage | str | None = None,
) -> ReportLocalization:
    """Return localization data for an explicit or configured report language."""
    report_language = (
        get_configured_report_language()
        if language is None
        else ReportLanguage.from_value(language)
    )
    if report_language is ReportLanguage.ZH:
        return ZH_REPORT_LOCALIZATION
    return EN_REPORT_LOCALIZATION


def _title_value(value: str) -> str:
    return value.replace("_", " ").title()


__all__ = [
    "ReportLanguage",
    "ReportLocalization",
    "get_configured_report_language",
    "get_report_localization",
]
