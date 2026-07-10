"""Interactive HTML rendering for investment research reports."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape
import math
from typing import Any

from parakeetnest.context.models import PortfolioPosition
from parakeetnest.models import (
    PositionDecision,
    PositionRecommendation,
)
from parakeetnest.research.models import (
    InvestmentResearchReport,
    ResearchPositionDecision,
    ResearchTickerReport,
)
from parakeetnest.research.localization import (
    ReportLanguage,
    ReportLocalization,
    get_report_localization,
)


class _InvestmentResearchReportFormattingHelpers:
    """Shared formatting helpers for investment research report renderers."""

    def _raw_evidence_lines(self, report: InvestmentResearchReport) -> list[str]:
        lines: list[str] = []
        lines.extend(f"- Report evidence: {note}" for note in report.evidence_notes)
        lines.extend(f"- Report source: {source}" for source in report.source_summaries)
        for ticker_report in report.ticker_reports:
            lines.append(f"- {ticker_report.ticker}: {ticker_report.summary}")
            for finding in ticker_report.findings:
                lines.append(
                    f"  - Finding: {finding.summary} (source: {finding.source})"
                )
                lines.extend(
                    f"    - Evidence note: {note}" for note in finding.evidence_notes
                )
            lines.extend(
                f"  - Public market fact: {fact}"
                for fact in ticker_report.public_market_facts
            )
            lines.extend(
                f"  - Yahoo profile fact: {fact}"
                for fact in ticker_report.profile_facts
            )
            lines.extend(
                f"  - Yahoo valuation fact: {fact}"
                for fact in ticker_report.valuation_facts
            )
            lines.extend(
                f"  - Financial statement fact: {fact}"
                for fact in ticker_report.financial_facts
            )
            lines.extend(
                f"  - Public news fact: {fact}" for fact in ticker_report.news_facts
            )
            lines.extend(
                f"  - Company fact: {fact}" for fact in ticker_report.company_facts
            )
            lines.extend(f"  - Macro fact: {fact}" for fact in ticker_report.macro_facts)
            lines.extend(
                f"  - Privacy-safe portfolio context: {line}"
                for line in _portfolio_context_lines(ticker_report)
            )
            for risk in ticker_report.risks:
                if risk.evidence_notes:
                    lines.append(f"  - Risk: {risk.summary}")
                    lines.extend(
                        f"    - Evidence note: {note}"
                        for note in risk.evidence_notes
                    )
            for catalyst in ticker_report.catalysts:
                if catalyst.evidence_notes:
                    lines.append(f"  - Catalyst: {catalyst.summary}")
                    lines.extend(
                        f"    - Evidence note: {note}"
                        for note in catalyst.evidence_notes
                    )
            lines.extend(
                f"  - Source: {source}" for source in ticker_report.source_summaries
            )
            lines.extend(
                f"  - Evidence note: {note}" for note in ticker_report.evidence_notes
            )
        return lines

    def _position_committee_review_lookup(
        self,
        report: InvestmentResearchReport,
    ) -> dict[str, ResearchPositionDecision]:
        return {
            review.ticker: review
            for review in report.position_committee_reviews
        }

    def _ticker_evidence(self, ticker_report: ResearchTickerReport) -> tuple[str, ...]:
        evidence: list[str] = []
        for finding in ticker_report.findings:
            evidence.append(f"{finding.source}: {finding.summary}")
            evidence.extend(
                f"{finding.source}: {note}" for note in finding.evidence_notes
            )
        evidence.extend(ticker_report.public_market_facts)
        evidence.extend(ticker_report.profile_facts)
        evidence.extend(ticker_report.valuation_facts)
        evidence.extend(ticker_report.financial_facts)
        evidence.extend(ticker_report.news_facts)
        evidence.extend(ticker_report.company_facts)
        evidence.extend(ticker_report.macro_facts)
        evidence.extend(_portfolio_context_lines(ticker_report))
        for risk in ticker_report.risks:
            if risk.evidence_notes:
                evidence.append(f"risk: {risk.summary}")
                evidence.extend(f"risk evidence: {note}" for note in risk.evidence_notes)
        for catalyst in ticker_report.catalysts:
            if catalyst.evidence_notes:
                evidence.append(f"catalyst: {catalyst.summary}")
                evidence.extend(
                    f"catalyst evidence: {note}" for note in catalyst.evidence_notes
                )
        evidence.extend(ticker_report.source_summaries)
        return tuple(dict.fromkeys(value for value in evidence if value))

    def _stable_portfolio_positions(
        self,
        report: InvestmentResearchReport,
    ) -> tuple[PortfolioPosition, ...]:
        if report.portfolio_context is None:
            return ()
        action_symbols = {
            decision.symbol
            for decision in report.position_decisions
            if decision.action_required or decision.human_review_required
        }
        return tuple(
            position
            for position in report.portfolio_context.positions
            if position.symbol not in action_symbols
        )

class InteractiveHtmlInvestmentResearchReportRenderer(
    _InvestmentResearchReportFormattingHelpers,
):
    """Render research reports into deterministic standalone HTML."""

    def __init__(
        self,
        language: ReportLanguage | str | None = None,
        localization: ReportLocalization | None = None,
    ) -> None:
        self._localization = localization or get_report_localization(language)

    def render(self, report: InvestmentResearchReport) -> str:
        """Return a standalone interactive HTML report."""
        sections = [
            "<!doctype html>",
            "<html>",
            '<head><meta charset="utf-8"></head>',
            (
                '<body style="font-family: -apple-system, BlinkMacSystemFont, '
                "Segoe UI, Arial, sans-serif; color: #111827; line-height: 1.5; "
                'margin: 0; padding: 24px; background: #f9fafb;">'
            ),
            self._render_html_header(report),
            self._render_html_human_review_notice(),
            self._render_html_position_cards(report),
            self._render_html_new_opportunities(report),
            self._render_html_raw_evidence(report),
            "</body>",
            "</html>",
        ]
        return "\n".join(section.rstrip() for section in sections).rstrip() + "\n"

    def _render_html_header(self, report: InvestmentResearchReport) -> str:
        l10n = self._localization
        tickers = ", ".join(report.tickers()) or l10n.not_available
        metadata = (
            f"{report.title} | Report Mode: {report.mode.value} "
            f"| Generated At: {report.generated_at.isoformat()} "
            f"| Tickers: {tickers}"
        )
        if l10n.language is ReportLanguage.ZH:
            metadata = (
                f"{report.title} | 报告模式: {report.mode.value} "
                f"| 生成时间: {report.generated_at.isoformat()} "
                f"| 标的: {tickers}"
            )
        return "\n".join(
            [
                (
                    '<h1 style="font-size: 28px; line-height: 1.2; margin: 0 0 '
                    f'8px;">{_html(l10n.report_title)}</h1>'
                ),
                (
                    '<p style="margin: 0 0 18px; color: #4b5563;">'
                    f"{_html(metadata)}</p>"
                ),
            ]
        )

    def _render_html_human_review_notice(self) -> str:
        l10n = self._localization
        return (
            '<p style="padding: 12px; background: #fff7ed; border-left: 4px solid '
            '#f97316; margin: 0 0 18px;">'
            f"<strong>{_html(l10n.human_review_required)}:</strong> "
            f"{_html(l10n.human_review_notice)}</p>"
        )

    def _render_html_position_cards(self, report: InvestmentResearchReport) -> str:
        cards: list[str] = []
        decisions = self._html_action_decisions(report)
        if decisions:
            cards.extend(
                self._render_html_decision_card(decision)
                for decision in decisions
            )
        else:
            position_reviews = self._position_committee_review_lookup(report)
            cards.extend(
                self._render_html_ticker_card(
                    ticker_report,
                    report,
                    position_reviews.get(ticker_report.ticker),
                )
                for ticker_report in report.ticker_reports
            )
        if not cards:
            cards.append(
                (
                    '<p style="margin: 0 0 18px;">'
                    f"{_html(self._localization.no_position_cards)}</p>"
                )
            )
        return "\n".join(
            [
                self._html_section_heading(
                    f"1. {self._localization.position_cards}"
                ),
                *cards,
            ]
        )

    def _render_html_decision_card(self, decision: PositionDecision) -> str:
        l10n = self._localization
        recommendation = self._recommendation_label(decision.recommendation)
        badges = [
            self._html_badge(
                self._label_value_badge(l10n.confidence, decision.confidence.value),
                kind="confidence",
            ),
        ]
        if decision.human_review_required:
            badges.append(self._html_badge(l10n.human_review_required, kind="review"))
        return self._html_collapsed_position_card(
            ticker=decision.symbol,
            recommendation=recommendation,
            badges=badges,
            border_color=self._recommendation_border_color(recommendation),
            body="\n".join(
                [
                    self._html_field(l10n.recommendation, recommendation),
                    self._html_field(
                        l10n.confidence,
                        self._localized_level(decision.confidence.value),
                    ),
                    self._html_field(
                        l10n.urgency,
                        self._localized_level(decision.urgency.value),
                    ),
                    self._html_field(l10n.rationale, decision.final_rationale),
                    self._html_field(
                        l10n.final_consensus,
                        (
                            f"{decision.final_rationale} "
                            f"{l10n.no_automatic_action_review_recommended}"
                        ),
                    ),
                    self._render_html_actionable_sizing(decision),
                    self._render_html_committee_discussion(
                        (
                            (l10n.dongdong, decision.dongdong_opinion),
                            (l10n.xixi, decision.xixi_opinion),
                            (l10n.yoyo, decision.yoyo_opinion),
                        )
                    ),
                    self._html_details(
                        l10n.factual_evidence,
                        [
                            self._html_list(
                                self._privacy_safe_values(decision.factual_evidence)
                            ),
                        ],
                    ),
                ]
            ),
        )

    def _render_html_ticker_card(
        self,
        ticker_report: ResearchTickerReport,
        report: InvestmentResearchReport,
        position_review: ResearchPositionDecision | None,
    ) -> str:
        l10n = self._localization
        recommendation_value = (
            position_review.recommendation
            if position_review is not None
            else report.committee_consensus.final_action
        )
        confidence_value = (
            position_review.confidence
            if position_review is not None
            else report.committee_consensus.confidence
        )
        rationale = (
            position_review.rationale
            if position_review is not None
            else report.committee_consensus.rationale
        )
        dongdong_opinion = (
            position_review.dongdong_opinion
            if position_review is not None
            else None
        )
        xixi_opinion = (
            position_review.xixi_opinion
            if position_review is not None
            else None
        )
        yoyo_opinion = (
            position_review.yoyo_opinion
            if position_review is not None
            else None
        )
        recommendation = self._localized_recommendation_text(
            recommendation_value
        )
        badges = [
            self._html_badge(
                self._label_value_badge(
                    l10n.confidence,
                    confidence_value,
                ),
                kind="confidence",
            ),
            self._html_badge(l10n.human_review_required, kind="review"),
        ]
        return self._html_collapsed_position_card(
            ticker=ticker_report.ticker,
            recommendation=recommendation,
            badges=badges,
            border_color=self._recommendation_border_color(recommendation),
            body="\n".join(
                [
                    self._html_field(l10n.recommendation, recommendation),
                    self._html_field(
                        l10n.confidence,
                        self._localized_level(confidence_value),
                    ),
                    self._html_field(l10n.rationale, ticker_report.summary),
                    self._html_field(
                        l10n.final_consensus,
                        (
                            f"{rationale} "
                            f"{l10n.no_automatic_action_review_recommended}"
                        ),
                    ),
                    self._render_html_committee_discussion(
                        (
                            (l10n.dongdong, dongdong_opinion),
                            (l10n.xixi, xixi_opinion),
                            (l10n.yoyo, yoyo_opinion),
                        )
                    ),
                    self._render_html_interpretation(ticker_report),
                    self._render_html_public_facts(ticker_report),
                    self._render_html_portfolio_context(ticker_report),
                    self._html_details(
                        l10n.factual_evidence,
                        [
                            self._html_list(
                                self._privacy_safe_values(
                                    (
                                        position_review.evidence
                                        if position_review is not None
                                        else self._ticker_evidence(ticker_report)
                                    )
                                )
                            ),
                        ],
                    ),
                ]
            ),
        )

    def _render_html_public_facts(self, ticker_report: ResearchTickerReport) -> str:
        title = (
            "公开事实"
            if self._localization.language is ReportLanguage.ZH
            else "Public facts"
        )
        yahoo_title = "Yahoo / market data"
        profile_title = "Yahoo / profile"
        valuation_title = "Yahoo / valuation"
        financials_title = "Financial statements"
        news_title = "Yahoo / news"
        sec_title = "SEC EDGAR"
        fred_title = "FRED / macro"
        return "\n".join(
            [
                (
                    '<div style="background: #f8fafc; border: 1px solid #e2e8f0; '
                    'border-radius: 8px; padding: 10px; margin: 10px 0;">'
                ),
                (
                    '<p style="margin: 0 0 6px;"><strong>'
                    f"{_html(title)}</strong></p>"
                ),
                self._html_section_label(yahoo_title),
                self._html_list(ticker_report.public_market_facts),
                self._html_section_label(profile_title),
                self._html_list(ticker_report.profile_facts),
                self._html_section_label(valuation_title),
                self._html_list(ticker_report.valuation_facts),
                self._html_section_label(financials_title),
                self._html_list(ticker_report.financial_facts),
                self._html_section_label(news_title),
                self._html_list(ticker_report.news_facts[:5]),
                self._html_section_label(sec_title),
                self._html_list(ticker_report.company_facts),
                self._html_section_label(fred_title),
                self._html_list(ticker_report.macro_facts),
                "</div>",
            ]
        )

    def _render_html_interpretation(
        self,
        ticker_report: ResearchTickerReport,
    ) -> str:
        title = (
            "委员会前分析"
            if self._localization.language is ReportLanguage.ZH
            else "Pre-committee analysis"
        )
        interpretation = ticker_report.fact_interpretation
        return "\n".join(
            [
                (
                    '<div style="background: #f8fafc; border: 1px solid #e2e8f0; '
                    'border-radius: 8px; padding: 10px; margin: 10px 0;">'
                ),
                (
                    '<p style="margin: 0 0 6px;"><strong>'
                    f"{_html(title)}</strong></p>"
                ),
                self._html_list(
                    (
                        f"valuation_label={interpretation.valuation_label}",
                        interpretation.profile_summary,
                        interpretation.valuation_summary,
                        interpretation.risk_summary,
                        interpretation.catalyst_summary,
                    )
                ),
                "</div>",
            ]
        )

    def _render_html_portfolio_context(
        self,
        ticker_report: ResearchTickerReport,
    ) -> str:
        title = (
            "组合背景（隐私安全桶）"
            if self._localization.language is ReportLanguage.ZH
            else "Portfolio context, privacy-safe"
        )
        values = list(_portfolio_context_lines(ticker_report))
        return "\n".join(
            [
                (
                    '<div style="background: #f8fafc; border: 1px solid #e2e8f0; '
                    'border-radius: 8px; padding: 10px; margin: 10px 0;">'
                ),
                (
                    '<p style="margin: 0 0 6px;"><strong>'
                    f"{_html(title)}</strong></p>"
                ),
                self._html_list(values),
                "</div>",
            ]
        )

    def _render_html_committee_discussion(
        self,
        opinions: Iterable[tuple[str, str | None]],
    ) -> str:
        title = (
            "委员会讨论"
            if self._localization.language is ReportLanguage.ZH
            else "Committee discussion"
        )
        return "\n".join(
            [
                (
                    '<div style="background: #f8fafc; border: 1px solid #e2e8f0; '
                    'border-radius: 8px; padding: 10px; margin: 10px 0;">'
                ),
                (
                    '<p style="margin: 0 0 6px;"><strong>'
                    f"{_html(title)}</strong></p>"
                ),
                *[self._html_field(label, value) for label, value in opinions],
                "</div>",
            ]
        )

    def _render_html_stable_holdings(self, report: InvestmentResearchReport) -> str:
        l10n = self._localization
        items: list[str] = []
        stable_decisions = tuple(
            decision
            for decision in report.position_decisions
            if not decision.action_required and not decision.human_review_required
        )
        for decision in stable_decisions:
            recommendation = self._recommendation_label(decision.recommendation)
            items.append(
                f"{decision.symbol}: {recommendation} "
                f"({l10n.confidence}: "
                f"{self._localized_level(decision.confidence.value)}). "
                f"{decision.final_rationale}"
            )
            if l10n.language is ReportLanguage.ZH:
                items[-1] = (
                    f"{decision.symbol}: {recommendation} "
                    f"({l10n.confidence}："
                    f"{self._localized_level(decision.confidence.value)})。"
                    f"{decision.final_rationale}"
                )
        if not items:
            for position in self._stable_portfolio_positions(report):
                separator = "，" if l10n.language is ReportLanguage.ZH else " "
                items.append(
                    f"{position.symbol}: {l10n.current_no_action}{separator}"
                    f"{l10n.sensitive_holding_data_hidden}"
                )
        stable_symbols = {decision.symbol for decision in stable_decisions}
        if report.portfolio_decision_summary is not None:
            for symbol in report.portfolio_decision_summary.no_action_positions:
                if symbol not in stable_symbols:
                    items.append(f"{symbol}: {l10n.current_no_action}")
        if not items:
            items.append(l10n.no_stable_holdings)
        return "\n".join(
            [
                self._html_section_heading(f"3. {l10n.stable_holdings}"),
                self._html_details(l10n.show_stable_holdings, [self._html_list(items)]),
            ]
        )

    def _render_html_new_opportunities(self, report: InvestmentResearchReport) -> str:
        l10n = self._localization
        cards: list[str] = []
        for opportunity in report.new_opportunities:
            recommendation = self._recommendation_label(opportunity.suggested_action)
            cards.append(
                self._html_card(
                    title=f"{opportunity.symbol} - {recommendation}",
                    border_color=self._recommendation_border_color(recommendation),
                    body="\n".join(
                        [
                            self._html_badge_row(
                                [
                                    self._html_badge(
                                        recommendation,
                                        kind="recommendation",
                                    ),
                                    self._html_badge(
                                        self._label_value_badge(
                                            l10n.confidence,
                                            opportunity.confidence.value,
                                        ),
                                        kind="confidence",
                                    ),
                                ]
                            ),
                            self._html_field(l10n.recommendation, recommendation),
                            self._html_field(
                                l10n.confidence,
                                self._localized_level(opportunity.confidence.value),
                            ),
                            self._html_field(l10n.rationale, opportunity.rationale),
                            (
                                '<p style="margin: 8px 0 4px;">'
                                f"<strong>{_html(l10n.risks)}:</strong></p>"
                            ),
                            self._html_list(opportunity.risks),
                        ]
                    ),
                )
            )
        if not cards:
            cards.append(
                f'<p style="margin: 0 0 18px;">{_html(report.watchlist_review)}</p>'
            )
        return "\n".join(
            [self._html_section_heading(f"2. {l10n.new_opportunities}"), *cards]
        )

    def _render_html_raw_evidence(self, report: InvestmentResearchReport) -> str:
        l10n = self._localization
        raw_lines = tuple(
            line.lstrip("- ").strip()
            for line in self._raw_evidence_lines(report)
        )
        evidence = self._privacy_safe_values(raw_lines) or (l10n.no_raw_evidence,)
        return "\n".join(
            [
                self._html_section_heading(f"3. {l10n.raw_evidence}"),
                self._html_details(l10n.show_raw_evidence, [self._html_list(evidence)]),
            ]
        )

    def _render_html_actionable_sizing(self, decision: PositionDecision) -> str:
        l10n = self._localization
        fields = [
            (l10n.current_status, self._current_status_label(decision)),
            (
                l10n.suggested_action,
                self._recommendation_label(decision.recommendation),
            ),
            (l10n.share_guidance, self._share_guidance(decision)),
            (l10n.target_weight, self._target_weight_guidance(decision)),
            (l10n.execution_style, l10n.review_in_tranches_no_trade),
        ]
        return "\n".join(
            [
                (
                    '<div style="background: #f8fafc; border: 1px solid #e2e8f0; '
                    'border-radius: 8px; padding: 10px; margin: 10px 0;">'
                ),
                (
                    '<p style="margin: 0 0 6px;"><strong>'
                    f"{_html(l10n.action_and_sizing_review)}</strong></p>"
                ),
                *[self._html_field(label, value) for label, value in fields],
                "</div>",
            ]
        )

    def _current_status_label(self, decision: PositionDecision) -> str:
        if decision.recommendation is PositionRecommendation.SELL:
            return self._localization.high_risk
        if decision.recommendation is PositionRecommendation.TRIM:
            return self._localization.overweight
        return self._localization.position_needs_review

    def _share_guidance(self, decision: PositionDecision) -> str:
        explicit = _first_existing_attr(
            decision,
            (
                "suggested_share_range",
                "suggested_shares_range",
                "approx_share_range",
                "estimated_share_range",
            ),
        )
        if explicit is not None:
            return _format_share_guidance(
                explicit,
                language=self._localization.language,
                fallback=self._localization.share_count_manual_confirmation,
            )
        numeric = _first_existing_attr(
            decision,
            (
                "suggested_shares",
                "estimated_shares",
                "shares_to_trade",
                "shares_to_buy",
                "shares_to_sell",
            ),
        )
        if numeric is not None:
            return _format_share_guidance(
                numeric,
                language=self._localization.language,
                fallback=self._localization.share_count_manual_confirmation,
            )
        return self._localization.share_count_manual_confirmation

    def _target_weight_guidance(self, decision: PositionDecision) -> str:
        explicit = _first_existing_attr(
            decision,
            (
                "target_weight_range",
                "target_weight_band",
                "target_risk_band",
            ),
        )
        if explicit is not None:
            return _format_weight_guidance(
                explicit,
                fallback=self._localization.target_weight_manual_confirmation,
                label=self._localization.target_weight,
            )
        lower = getattr(decision, "target_weight_min", None)
        upper = getattr(decision, "target_weight_max", None)
        if lower is not None and upper is not None:
            return _format_weight_guidance(
                (lower, upper),
                fallback=self._localization.target_weight_manual_confirmation,
                label=self._localization.target_weight,
            )
        target = getattr(decision, "target_weight", None)
        if target is not None:
            return _format_weight_guidance(
                target,
                fallback=self._localization.target_weight_manual_confirmation,
                label=self._localization.target_weight,
            )
        return self._localization.target_weight_manual_confirmation

    def _html_action_decisions(
        self,
        report: InvestmentResearchReport,
    ) -> tuple[PositionDecision, ...]:
        return tuple(
            decision
            for decision in report.position_decisions
            if decision.action_required or decision.human_review_required
        )

    def _html_section_heading(self, text: str) -> str:
        return (
            '<h2 style="font-size: 20px; margin: 24px 0 10px; color: #111827;">'
            f"{_html(text)}</h2>"
        )

    def _html_card(self, *, title: str, border_color: str, body: str) -> str:
        return "\n".join(
            [
                (
                    '<div style="background: #ffffff; border: 1px solid #e5e7eb; '
                    f"border-left: 5px solid {border_color}; border-radius: 10px; "
                    'padding: 14px; margin: 12px 0;">'
                ),
                (
                    '<h3 style="color: #111827; font-weight: 800; margin: 0 0 8px;">'
                    '<span style="font-size: 18px;">'
                    f"{_html(title)}</span></h3>"
                ),
                body,
                "</div>",
            ]
        )

    def _html_collapsed_position_card(
        self,
        *,
        ticker: str,
        recommendation: str,
        badges: Iterable[str],
        border_color: str,
        body: str,
    ) -> str:
        badge_markup = " ".join(
            (self._html_badge(recommendation, kind="recommendation"), *badges)
        )
        return "\n".join(
            [
                (
                    '<details style="background: #ffffff; border: 1px solid #e5e7eb; '
                    f"border-left: 5px solid {border_color}; border-radius: 10px; "
                    'padding: 14px; margin: 12px 0;">'
                ),
                (
                    '<summary style="cursor: pointer; color: #111827; '
                    'font-weight: 800;">'
                    '<span style="font-size: 18px; margin-right: 8px;">'
                    f"{_html(ticker)}</span>"
                    f"{badge_markup}</summary>"
                ),
                body,
                "</details>",
            ]
        )

    def _html_field(self, label: str, value: str | None) -> str:
        return (
            '<p style="margin: 8px 0;"><strong>'
            f"{_html(label)}:</strong> {_html(self._fallback(value))}</p>"
        )

    def _html_section_label(self, label: str) -> str:
        return f'<p style="margin: 8px 0;"><strong>{_html(label)}:</strong></p>'

    def _html_list(self, values: Iterable[str]) -> str:
        normalized = tuple(value.strip() for value in values if value.strip())
        items = normalized or (self._localization.no_available_info,)
        lines = ['<ul style="margin: 8px 0 0 20px; padding: 0;">']
        lines.extend(f"<li>{_html(item)}</li>" for item in items)
        lines.append("</ul>")
        return "\n".join(lines)

    def _html_details(self, summary: str, blocks: Iterable[str]) -> str:
        return "\n".join(
            [
                '<details style="margin-top: 12px;">',
                (
                    '<summary style="cursor: pointer; color: #374151; '
                    f'font-weight: 700;">{_html(summary)}</summary>'
                ),
                *blocks,
                "</details>",
            ]
        )

    def _html_badge_row(self, badges: Iterable[str]) -> str:
        return '<p style="margin: 8px 0 10px;">' + " ".join(badges) + "</p>"

    def _html_badge(self, label: str, *, kind: str) -> str:
        background, color = self._badge_colors(label, kind=kind)
        return (
            f'<span style="display: inline-block; background: {background}; '
            f"color: {color}; padding: 3px 8px; border-radius: 999px; "
            f'font-size: 12px; font-weight: 700; margin: 0 6px 6px 0;">'
            f"{_html(label)}</span>"
        )

    def _badge_colors(self, label: str, *, kind: str) -> tuple[str, str]:
        normalized = label.strip().lower()
        if kind == "confidence":
            if "high" in normalized or "高" in normalized:
                return "#dcfce7", "#166534"
            if "medium" in normalized or "中" in normalized:
                return "#fef3c7", "#92400e"
            return "#f3f4f6", "#374151"
        if kind == "review":
            return "#fee2e2", "#991b1b"
        if kind == "urgency":
            if "high" in normalized or "高" in normalized:
                return "#fee2e2", "#991b1b"
            if "medium" in normalized or "中" in normalized:
                return "#ffedd5", "#9a3412"
            return "#e5e7eb", "#374151"
        if any(
            value in normalized
            for value in ("trim", "reduce", "sell", "required", "减仓", "卖出")
        ):
            return "#ffedd5", "#9a3412"
        if any(value in normalized for value in ("watch", "new opportunity", "观察")):
            return "#f3e8ff", "#6b21a8"
        if any(value in normalized for value in ("buy", "add", "买入")):
            return "#dcfce7", "#166534"
        return "#e0f2fe", "#075985"

    def _recommendation_border_color(self, label: str) -> str:
        normalized = label.strip().lower()
        if any(
            value in normalized
            for value in ("trim", "reduce", "sell", "required", "减仓", "卖出")
        ):
            return "#f97316"
        if any(value in normalized for value in ("watch", "new opportunity", "观察")):
            return "#a855f7"
        if any(value in normalized for value in ("buy", "add", "买入")):
            return "#22c55e"
        return "#60a5fa"

    def _localized_level(self, value: str) -> str:
        return self._localization.level_label(value)

    def _recommendation_label(self, value: PositionRecommendation | str) -> str:
        return self._localization.recommendation_label(value)

    def _localized_recommendation_text(self, value: str) -> str:
        normalized = str(value).strip().lower().replace(" ", "_")
        try:
            return self._recommendation_label(PositionRecommendation(normalized))
        except ValueError:
            return self._localization.recommendation_label(str(value))

    def _privacy_safe_values(self, values: Iterable[str]) -> tuple[str, ...]:
        return tuple(value for value in values if not _looks_portfolio_sensitive(value))

    def _fallback(self, value: str | None) -> str:
        if value is None:
            return self._localization.not_available
        normalized = value.strip()
        return normalized or self._localization.not_available

    def _label_value_badge(self, label: str, value: str) -> str:
        separator = "：" if self._localization.language is ReportLanguage.ZH else ": "
        return f"{label}{separator}{self._localized_level(value)}"


def _first_existing_attr(obj: object, names: Iterable[str]) -> object | None:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _format_share_guidance(
    value: object,
    *,
    language: ReportLanguage,
    fallback: str,
) -> str:
    if isinstance(value, tuple | list) and len(value) >= 2:
        lower = _coerce_positive_float(value[0])
        upper = _coerce_positive_float(value[1])
        if lower is not None and upper is not None:
            return _format_share_range(lower, upper, language=language)
    numeric = _coerce_positive_float(value)
    if numeric is None:
        return fallback
    lower, upper = _approximate_share_range(numeric)
    return _format_share_range(lower, upper, language=language)


def _format_share_range(
    lower: float,
    upper: float,
    *,
    language: ReportLanguage,
) -> str:
    low = max(1, int(round(min(lower, upper))))
    high = max(low, int(round(max(lower, upper))))
    if language is ReportLanguage.ZH:
        return f"约 {low:g}–{high:g} 股"
    return f"approximately {low:g}–{high:g} shares"


def _approximate_share_range(value: float) -> tuple[float, float]:
    if value <= 10:
        lower = max(1, math.floor(value))
        upper = max(lower + 1, math.ceil(value))
        return lower, upper
    if value <= 100:
        step = 5 if value <= 50 else 10
    else:
        step = 10 if value <= 250 else 25
    lower = max(step, math.floor(value / step) * step)
    upper = max(lower + step, math.ceil(value / step) * step)
    return lower, upper


def _format_weight_guidance(value: object, *, fallback: str, label: str) -> str:
    if isinstance(value, str):
        text = value.strip()
        return text or fallback
    if isinstance(value, tuple | list) and len(value) >= 2:
        lower = _coerce_positive_float(value[0])
        upper = _coerce_positive_float(value[1])
        if lower is not None and upper is not None:
            return f"{label} {_format_percent(lower)}–{_format_percent(upper)}"
    numeric = _coerce_positive_float(value)
    if numeric is not None:
        return f"{label} {_format_percent(numeric)}"
    return fallback


def _coerce_positive_float(value: object) -> float | None:
    try:
        number = abs(float(value))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _looks_portfolio_sensitive(value: str) -> bool:
    normalized = value.lower()
    sensitive_terms = (
        "position value",
        "market value",
        "total portfolio",
        "total equity",
        "total market value",
        "total cash",
        "cash balance",
        "cash:",
        "shares held",
        " shares",
        "$",
        "市值",
        "持仓市值",
        "总资产",
        "总市值",
        "现金",
        "现金余额",
        "股",
        "持有",
        "成本",
        "盈亏",
    )
    return any(term in normalized for term in sensitive_terms)


def _portfolio_context_lines(ticker_report: ResearchTickerReport) -> tuple[str, ...]:
    lines: list[str] = []
    summary = ticker_report.portfolio_summary
    if summary is not None:
        lines.extend(
            (
                f"portfolio privacy level: {summary.privacy_level}",
                f"number of positions: {summary.number_of_positions}",
                f"cash allocation bucket: {summary.cash_allocation_bucket}",
                f"concentration level: {summary.concentration_level}",
                f"largest position bucket: {summary.largest_position_bucket}",
                f"top5 concentration bucket: {summary.top5_concentration_bucket}",
                f"dominant sector: {summary.dominant_sector or 'unknown'}",
                f"style exposure: {summary.style_exposure}",
            )
        )
    position_context = ticker_report.position_context
    if position_context is not None:
        lines.extend(
            (
                f"position size bucket: {position_context.position_size_bucket}",
                f"rank bucket: {position_context.portfolio_rank_bucket}",
                f"return bucket: {position_context.unrealized_return_bucket}",
                f"holding role: {position_context.holding_role}",
                f"add allowed: {position_context.add_allowed}",
                f"trim candidate: {position_context.trim_candidate}",
                f"position privacy level: {position_context.privacy_level}",
            )
        )
    return tuple(lines)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{float(value) * 100:.1f}%"


def render_investment_research_report_interactive_html(
    report: InvestmentResearchReport,
    language: ReportLanguage | str | None = None,
) -> str:
    """Render an investment research report as standalone interactive HTML."""
    return InteractiveHtmlInvestmentResearchReportRenderer(language).render(report)


def _html(value: Any) -> str:
    return escape(str(value), quote=True)


__all__ = [
    "InteractiveHtmlInvestmentResearchReportRenderer",
    "render_investment_research_report_interactive_html",
]
