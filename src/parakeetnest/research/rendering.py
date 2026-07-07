"""Email-friendly Markdown rendering for investment research reports."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from html import escape
import math
from typing import Any

from parakeetnest.context.models import PortfolioPosition
from parakeetnest.models import (
    NewOpportunity,
    PositionDecision,
    PositionRecommendation,
)
from parakeetnest.research.models import (
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
)


class InvestmentResearchReportRenderer:
    """Render research reports into deterministic email-friendly Markdown."""

    def render(self, report: InvestmentResearchReport) -> str:
        """Return a Markdown report suitable for an email body."""
        if report.mode is ReportMode.EVENING:
            sections = self._render_evening_sections(report)
        else:
            sections = self._render_morning_sections(report)
        return "\n\n".join(section.rstrip() for section in sections).rstrip() + "\n"

    def _render_morning_sections(self, report: InvestmentResearchReport) -> list[str]:
        return [
            self._render_morning_header(report),
            self._render_action_required(report),
            self._render_position_cards(report),
            self._render_stable_holdings(report),
            self._render_new_opportunities(report),
            self._render_market_overview(report),
            self._render_raw_evidence(report),
        ]

    def _render_morning_header(self, report: InvestmentResearchReport) -> str:
        tickers = ", ".join(report.tickers()) or "None"
        return "\n".join(
            [
                "# Morning Investment Report",
                "",
                report.title,
                f"Report Mode: {report.mode.value}",
                f"Generated At: {report.generated_at.isoformat()}",
                f"Tickers: {tickers}",
            ]
        )

    def _render_action_required(self, report: InvestmentResearchReport) -> str:
        lines = [
            "## 1. Action Required",
            "",
            (
                "Positions requiring user review or decision. This report is "
                "advisory guidance and does not take action for you."
            ),
            "",
        ]
        action_decisions = tuple(
            decision
            for decision in report.position_decisions
            if decision.action_required or decision.human_review_required
        )
        if action_decisions:
            for decision in action_decisions:
                lines.append(
                    "- "
                    f"{decision.symbol}: {self._recommendation_label(decision.recommendation)} "
                    f"({decision.confidence.value} confidence, {decision.urgency.value} urgency). "
                    "User review recommended."
                )
        else:
            lines.append("- No position decisions currently require user action.")
        if report.portfolio_decision_summary is not None:
            for item in report.portfolio_decision_summary.action_items:
                lines.append(f"- Portfolio action item: {item}")
        return "\n".join(lines)

    def _render_position_cards(self, report: InvestmentResearchReport) -> str:
        lines = ["## 2. Position Cards"]
        decisions = tuple(
            decision
            for decision in report.position_decisions
            if decision.action_required or decision.human_review_required
        )
        if decisions:
            for decision in decisions:
                lines.append("")
                lines.append(self._render_decision_card(decision))
            return "\n".join(lines)

        ticker_reports = tuple(report.ticker_reports)
        if not ticker_reports:
            lines.extend(["", "- No action-required position cards available."])
            return "\n".join(lines)

        opinions = self._committee_opinion_lookup(report)
        for ticker_report in ticker_reports:
            lines.append("")
            lines.append(self._render_ticker_card(ticker_report, report, opinions))
        return "\n".join(lines)

    def _render_decision_card(self, decision: PositionDecision) -> str:
        recommendation = self._recommendation_label(decision.recommendation)
        lines = [
            f"### {decision.symbol} — {recommendation}",
            "",
            f"**Recommendation:** {recommendation}  ",
            f"**Confidence:** {self._title_value(decision.confidence.value)}  ",
            f"**Rationale:** {decision.final_rationale}",
            "",
            f"**Dongdong:** {self._fallback(decision.dongdong_opinion)}  ",
            f"**Xixi:** {self._fallback(decision.xixi_opinion)}  ",
            f"**Youyou:** {self._fallback(decision.youyou_opinion)}  ",
            "**Final consensus:** "
            f"{decision.final_rationale} No automatic action. User review recommended.",
            "",
            "<details>",
            "<summary>Factual evidence</summary>",
            "",
        ]
        lines.extend(self._bullet_lines(decision.factual_evidence))
        lines.extend(["", "</details>"])
        return "\n".join(lines)

    def _render_ticker_card(
        self,
        ticker_report: ResearchTickerReport,
        report: InvestmentResearchReport,
        opinions: dict[str, str],
    ) -> str:
        recommendation = self._title_value(report.committee_consensus.final_action)
        lines = [
            f"### {ticker_report.ticker} — {recommendation}",
            "",
            f"**Recommendation:** {recommendation}  ",
            f"**Confidence:** {self._title_value(report.committee_consensus.confidence)}  ",
            f"**Rationale:** {ticker_report.summary}",
            "",
            f"**Dongdong:** {opinions.get('dongdong', 'Not available')}  ",
            f"**Xixi:** {opinions.get('xixi', 'Not available')}  ",
            f"**Youyou:** {opinions.get('youyou', 'Not available')}  ",
            "**Final consensus:** "
            f"{report.committee_consensus.rationale} No automatic action. User review recommended.",
            "",
            "<details>",
            "<summary>Factual evidence</summary>",
            "",
        ]
        evidence = self._ticker_evidence(ticker_report)
        lines.extend(self._bullet_lines(evidence))
        lines.extend(["", "</details>"])
        return "\n".join(lines)

    def _render_stable_holdings(self, report: InvestmentResearchReport) -> str:
        lines = [
            "## 3. Stable Holdings",
            "",
            "<details>",
            "<summary>Stable holdings</summary>",
            "",
        ]
        stable_decisions = tuple(
            decision
            for decision in report.position_decisions
            if not decision.action_required and not decision.human_review_required
        )
        if stable_decisions:
            for decision in stable_decisions:
                lines.append(
                    "- "
                    f"{decision.symbol}: {self._recommendation_label(decision.recommendation)} "
                    f"({decision.confidence.value} confidence). {decision.final_rationale}"
                )
        else:
            stable_positions = self._stable_portfolio_positions(report)
            if stable_positions:
                for position in stable_positions:
                    details = [
                        f"{position.symbol}: {position.quantity:g} shares",
                        f"value {_format_money(position.market_value)}",
                    ]
                    if position.weight is not None:
                        details.append(f"weight {_format_percent(position.weight)}")
                    lines.append(f"- {', '.join(details)}")
            else:
                lines.append("- No stable holdings available.")

        stable_symbols = {decision.symbol for decision in stable_decisions}
        if report.portfolio_decision_summary is not None:
            for symbol in report.portfolio_decision_summary.no_action_positions:
                if symbol in stable_symbols:
                    continue
                lines.append(f"- {symbol}: no action currently recommended.")
        lines.extend(["", "</details>"])
        return "\n".join(lines)

    def _render_new_opportunities(self, report: InvestmentResearchReport) -> str:
        lines = ["## 4. New Opportunities", ""]
        if report.new_opportunities:
            for opportunity in report.new_opportunities:
                lines.extend(self._render_opportunity(opportunity))
        else:
            lines.append(f"- {report.watchlist_review}")
        return "\n".join(lines)

    def _render_opportunity(self, opportunity: NewOpportunity) -> list[str]:
        return [
            (
                f"### {opportunity.symbol} — "
                f"{self._recommendation_label(opportunity.suggested_action)}"
            ),
            "",
            (
                "**Recommendation:** "
                f"{self._recommendation_label(opportunity.suggested_action)}  "
            ),
            f"**Confidence:** {self._title_value(opportunity.confidence.value)}  ",
            f"**Rationale:** {opportunity.rationale}",
            "",
            "**Risks:**",
            *self._bullet_lines(opportunity.risks),
            "",
        ]

    def _render_market_overview(self, report: InvestmentResearchReport) -> str:
        lines = [
            "## 5. Market Overview",
            "",
            f"- {report.market_summary}",
            f"- Portfolio context: {report.portfolio_review}",
        ]
        if report.portfolio_decision_summary is not None:
            lines.append(
                f"- Portfolio view: {report.portfolio_decision_summary.overall_portfolio_view}"
            )
            lines.extend(
                f"- Concentration risk: {risk}"
                for risk in report.portfolio_decision_summary.concentration_risks
            )
            lines.extend(
                f"- Sector exposure: {note}"
                for note in report.portfolio_decision_summary.sector_exposure_notes
            )
            lines.extend(
                f"- Cash allocation: {note}"
                for note in report.portfolio_decision_summary.cash_allocation_notes
            )
        return "\n".join(lines)

    def _render_raw_evidence(self, report: InvestmentResearchReport) -> str:
        lines = [
            "## 6. Raw Evidence",
            "",
            "<details>",
            "<summary>Raw evidence</summary>",
            "",
        ]
        raw_lines = self._raw_evidence_lines(report)
        lines.extend(raw_lines if raw_lines else ["- No raw evidence available."])
        lines.extend(["", "</details>"])
        return "\n".join(lines)

    def _raw_evidence_lines(self, report: InvestmentResearchReport) -> list[str]:
        lines: list[str] = []
        lines.extend(f"- Report evidence: {note}" for note in report.evidence_notes)
        lines.extend(f"- Report source: {source}" for source in report.source_summaries)
        for ticker_report in report.ticker_reports:
            lines.append(f"- {ticker_report.ticker}: {ticker_report.summary}")
            lines.extend(f"  - Bull case: {value}" for value in ticker_report.bull_case)
            lines.extend(f"  - Bear case: {value}" for value in ticker_report.bear_case)
            for finding in ticker_report.findings:
                lines.append(
                    f"  - Finding: {finding.summary} (source: {finding.source})"
                )
                lines.extend(
                    f"    - Evidence note: {note}" for note in finding.evidence_notes
                )
            lines.extend(
                f"  - Source: {source}" for source in ticker_report.source_summaries
            )
            lines.extend(
                f"  - Evidence note: {note}" for note in ticker_report.evidence_notes
            )
        return lines

    def _committee_opinion_lookup(
        self,
        report: InvestmentResearchReport,
    ) -> dict[str, str]:
        opinions: dict[str, str] = {}
        for opinion in report.committee_opinions:
            opinions[opinion.persona_id] = opinion.reasoning_summary
        return opinions

    def _ticker_evidence(self, ticker_report: ResearchTickerReport) -> tuple[str, ...]:
        evidence: list[str] = []
        evidence.extend(ticker_report.evidence)
        evidence.extend(ticker_report.bull_case)
        evidence.extend(ticker_report.bear_case)
        evidence.extend(risk.summary for risk in ticker_report.risks)
        evidence.extend(catalyst.summary for catalyst in ticker_report.catalysts)
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

    def _bullet_lines(self, values: Iterable[str]) -> list[str]:
        normalized = tuple(value.strip() for value in values if value.strip())
        if not normalized:
            return ["- Not available"]
        return [f"- {value}" for value in normalized]

    def _recommendation_label(self, value: PositionRecommendation | str) -> str:
        raw_value = (
            value.value if isinstance(value, PositionRecommendation) else str(value)
        )
        return raw_value.replace("_", " ").title()

    def _title_value(self, value: str) -> str:
        return value.replace("_", " ").title()

    def _fallback(self, value: str | None) -> str:
        if value is None:
            return "Not available"
        normalized = value.strip()
        return normalized or "Not available"

    def _render_evening_sections(self, report: InvestmentResearchReport) -> list[str]:
        sections = [
            self._render_header(report),
            self._render_market_summary(report, label="Market Recap"),
            self._render_portfolio_review(report, label="Portfolio Review"),
            self._render_portfolio_summary(report),
            self._render_watchlist_review(report, label="Watchlist Review"),
            self._render_what_changed(report),
            self._render_ticker_reports(report.ticker_reports),
            self._render_committee_opinions(
                report,
                labels={
                    "dongdong": "Dongdong’s Opportunity Review",
                    "xixi": "Xixi’s Fundamental Review",
                    "youyou": "Youyou’s Risk Review",
                },
            ),
            self._render_committee_portfolio_view(report),
            self._render_committee_consensus(report),
            self._render_confidence(report),
            self._render_key_risks(report.ticker_reports),
            self._render_tomorrows_focus(report),
            self._render_suggested_followups(report),
            self._render_evidence_notes(report),
        ]
        return sections

    def _render_header(self, report: InvestmentResearchReport) -> str:
        tickers = ", ".join(report.tickers()) or "None"
        return "\n".join(
            [
                "Header",
                report.title,
                f"Report Mode: {report.mode.value}",
                f"Generated At: {report.generated_at.isoformat()}",
                f"Tickers: {tickers}",
            ]
        )

    def _render_market_summary(
        self,
        report: InvestmentResearchReport,
        *,
        label: str,
    ) -> str:
        return "\n".join([label, f"- {report.market_summary}"])

    def _render_portfolio_review(
        self,
        report: InvestmentResearchReport,
        *,
        label: str,
    ) -> str:
        return "\n".join([label, f"- {report.portfolio_review}"])

    def _render_portfolio_summary(self, report: InvestmentResearchReport) -> str:
        lines = ["Portfolio Summary"]
        portfolio = report.portfolio_context
        if portfolio is None:
            lines.append("- No portfolio context available.")
            return "\n".join(lines)

        total_value = portfolio.total_value or portfolio.total_equity
        cash_balance = portfolio.cash_balance or portfolio.total_cash
        lines.extend(
            [
                f"- Total Portfolio Value: {_format_money(total_value)}",
                f"- Cash Balance: {_format_money(cash_balance)}",
                "- Holdings:",
            ]
        )
        if portfolio.positions:
            for position in portfolio.positions:
                details = [
                    f"{position.symbol}: {position.quantity:g} shares",
                    f"value {_format_money(position.market_value)}",
                ]
                if position.weight is not None:
                    details.append(f"weight {_format_percent(position.weight)}")
                lines.append(f"  - {', '.join(details)}")
        else:
            lines.append("  - None")

        lines.append("- Portfolio Weights:")
        if portfolio.allocation_by_symbol:
            lines.extend(
                f"  - {allocation.category}: {_format_percent(allocation.percent)}"
                for allocation in portfolio.allocation_by_symbol
            )
        elif portfolio.positions:
            lines.extend(
                f"  - {position.symbol}: {_format_percent(position.weight)}"
                for position in portfolio.positions
                if position.weight is not None
            )
        else:
            lines.append("  - None")
        return "\n".join(lines)

    def _render_watchlist_review(
        self,
        report: InvestmentResearchReport,
        *,
        label: str,
    ) -> str:
        return "\n".join([label, f"- {report.watchlist_review}"])

    def _render_focus(self, report: InvestmentResearchReport, *, label: str) -> str:
        lines = [label]
        if not report.ticker_reports:
            lines.append("- No ticker reports were generated.")
            return "\n".join(lines)

        lines.append(f"- Coverage: {len(report.ticker_reports)} ticker(s).")
        lines.append(
            "- Committee view: "
            f"{report.committee_consensus.final_action.upper()} "
            f"({report.committee_consensus.confidence} confidence)."
        )
        for ticker_report in report.ticker_reports:
            lines.append(
                "- "
                f"{ticker_report.ticker}: {ticker_report.summary}"
            )
        return "\n".join(lines)

    def _render_what_changed(self, report: InvestmentResearchReport) -> str:
        lines = ["What Changed"]
        if not report.ticker_reports:
            lines.append("- No ticker reports were generated.")
            return "\n".join(lines)
        for ticker_report in report.ticker_reports:
            lines.append(f"- {ticker_report.ticker}: {ticker_report.summary}")
            for finding in ticker_report.findings:
                lines.append(f"  - {finding.summary} (source: {finding.source})")
        return "\n".join(lines)

    def _render_committee_opinions(
        self,
        report: InvestmentResearchReport,
        *,
        labels: dict[str, str],
    ) -> str:
        lines = ["Committee Judgment"]
        for opinion in report.committee_opinions:
            section_label = labels.get(
                opinion.persona_id,
                f"{opinion.display_name}'s Opinion",
            )
            lines.extend(
                [
                    f"{section_label} ({opinion.role_title})",
                    f"- Stance: {opinion.stance}",
                    f"- Reasoning: {opinion.reasoning_summary}",
                    "- Evidence:",
                ]
            )
            lines.extend(f"  - {value}" for value in opinion.evidence_considered)
            lines.append(f"- Concern: {opinion.key_concern}")
            lines.append(f"- Suggested Action: {opinion.suggested_action}")
        if len(lines) == 1:
            lines.append("- No committee opinions.")
        return "\n".join(lines)

    def _render_committee_portfolio_view(
        self,
        report: InvestmentResearchReport,
    ) -> str:
        lines = ["Committee Portfolio View"]
        for view in report.committee_portfolio_views:
            lines.extend(
                [
                    f"- {view.agent_name} ({view.role})",
                    f"  Portfolio View: {view.portfolio_view}",
                ]
            )
        if len(lines) == 1:
            lines.append("- No committee portfolio observations.")
        return "\n".join(lines)

    def _render_committee_consensus(self, report: InvestmentResearchReport) -> str:
        consensus = report.committee_consensus
        return "\n".join(
            [
                "Committee Consensus",
                f"- Final Action: {consensus.final_action.upper()}",
                f"- Horizon: {consensus.horizon}",
                f"- Final Risk Posture: {consensus.final_risk_posture}",
                f"- Rationale: {consensus.rationale}",
            ]
        )

    def _render_confidence(self, report: InvestmentResearchReport) -> str:
        return "\n".join(["Confidence", f"- {report.committee_consensus.confidence}"])

    def _render_ticker_reports(
        self,
        ticker_reports: Iterable[ResearchTickerReport],
    ) -> str:
        lines = ["Factual Ticker Context"]
        for ticker_report in ticker_reports:
            lines.extend(
                [
                    f"- {ticker_report.ticker}",
                    f"  Summary: {ticker_report.summary}",
                ]
            )
            lines.extend(self._render_values("Bull Case", ticker_report.bull_case))
            lines.extend(self._render_values("Bear Case", ticker_report.bear_case))
            lines.extend(self._render_findings(ticker_report.findings))
            lines.extend(self._render_values("Sources", ticker_report.source_summaries))
        if len(lines) == 1:
            lines.append("- No ticker reports.")
        return "\n".join(lines)

    def _render_key_risks(
        self,
        ticker_reports: Iterable[ResearchTickerReport],
    ) -> str:
        lines = ["Key Risks"]
        for ticker_report in ticker_reports:
            lines.append(f"- {ticker_report.ticker}")
            lines.extend(self._render_risk_items(ticker_report.risks))
        if len(lines) == 1:
            lines.append("- No risks.")
        return "\n".join(lines)

    def _render_upcoming_catalysts(
        self,
        ticker_reports: Iterable[ResearchTickerReport],
    ) -> str:
        lines = ["Upcoming Catalysts"]
        for ticker_report in ticker_reports:
            lines.append(f"- {ticker_report.ticker}")
            lines.extend(self._render_catalyst_items(ticker_report.catalysts))
        if len(lines) == 1:
            lines.append("- No catalysts.")
        return "\n".join(lines)

    def _render_todays_suggested_actions(
        self,
        report: InvestmentResearchReport,
    ) -> str:
        lines = ["Today's Suggested Actions"]
        lines.extend(
            f"- {action}"
            for action in report.committee_consensus.todays_suggested_actions
        )
        if len(lines) == 1:
            lines.append("- No suggested actions.")
        return "\n".join(lines)

    def _render_tomorrows_focus(self, report: InvestmentResearchReport) -> str:
        lines = ["Tomorrow’s Focus"]
        for ticker_report in report.ticker_reports:
            lines.append(f"- {ticker_report.ticker}")
            lines.extend(self._render_catalyst_items(ticker_report.catalysts))
        if len(lines) == 1:
            lines.append("- No tomorrow focus items.")
        return "\n".join(lines)

    def _render_suggested_followups(self, report: InvestmentResearchReport) -> str:
        lines = ["Suggested Follow-ups"]
        lines.extend(
            f"- {action}"
            for action in report.committee_consensus.todays_suggested_actions
        )
        if len(lines) == 1:
            lines.append("- No suggested follow-ups.")
        return "\n".join(lines)

    def _render_evidence_notes(self, report: InvestmentResearchReport) -> str:
        lines = ["Evidence Notes"]
        lines.extend(self._render_values("Report Notes", report.evidence_notes))
        lines.extend(self._render_values("Report Sources", report.source_summaries))
        for ticker_report in report.ticker_reports:
            lines.extend(
                self._render_values(
                    f"{ticker_report.ticker} Notes",
                    ticker_report.evidence_notes,
                )
            )
            for finding in ticker_report.findings:
                lines.extend(
                    self._render_values(
                        f"{ticker_report.ticker} Finding Evidence ({finding.source})",
                        finding.evidence_notes,
                    )
                )
            for risk in ticker_report.risks:
                lines.extend(
                    self._render_values(
                        f"{ticker_report.ticker} Risk Evidence",
                        risk.evidence_notes,
                    )
                )
            for catalyst in ticker_report.catalysts:
                lines.extend(
                    self._render_values(
                        f"{ticker_report.ticker} Catalyst Evidence",
                        catalyst.evidence_notes,
                    )
                )
        if len(lines) == 1:
            lines.append("- No evidence notes.")
        return "\n".join(lines)

    def _render_findings(self, findings: Iterable[ResearchFinding]) -> list[str]:
        normalized = tuple(findings)
        if not normalized:
            return []
        lines = ["  Findings:"]
        for finding in normalized:
            lines.append(f"    - {finding.summary} (source: {finding.source})")
        return lines

    def _render_risk_items(self, risks: Iterable[ResearchRisk]) -> list[str]:
        normalized = tuple(risks)
        if not normalized:
            return ["  - No risks."]
        return [f"  - {risk.summary}" for risk in normalized]

    def _render_catalyst_items(
        self,
        catalysts: Iterable[ResearchCatalyst],
    ) -> list[str]:
        normalized = tuple(catalysts)
        if not normalized:
            return ["  - No catalysts."]
        lines: list[str] = []
        for catalyst in normalized:
            if catalyst.horizon:
                lines.append(f"  - {catalyst.summary} (horizon: {catalyst.horizon})")
            else:
                lines.append(f"  - {catalyst.summary}")
        return lines

    def _render_values(self, label: str, values: Iterable[str]) -> list[str]:
        normalized = tuple(value.strip() for value in values if value.strip())
        if not normalized:
            return []
        return [f"  {label}:"] + [f"    - {value}" for value in normalized]

    def _value(self, value: Any) -> str:
        if isinstance(value, Enum):
            return value.value
        return str(value)


class InteractiveHtmlEmailInvestmentResearchReportRenderer(
    InvestmentResearchReportRenderer,
):
    """Render research reports into deterministic standalone HTML email."""

    def render(self, report: InvestmentResearchReport) -> str:
        """Return an inline-CSS HTML email body for a research report."""
        sections = [
            "<!doctype html>",
            "<html>",
            (
                '<body style="font-family: -apple-system, BlinkMacSystemFont, '
                "Segoe UI, Arial, sans-serif; color: #111827; line-height: 1.5; "
                'margin: 0; padding: 24px; background: #f9fafb;">'
            ),
            self._render_html_header(report),
            self._render_html_human_review_notice(),
            self._render_html_action_required(report),
            self._render_html_position_cards(report),
            self._render_html_stable_holdings(report),
            self._render_html_new_opportunities(report),
            self._render_html_market_overview(report),
            self._render_html_raw_evidence(report),
            "</body>",
            "</html>",
        ]
        return "\n".join(section.rstrip() for section in sections).rstrip() + "\n"

    def _render_html_header(self, report: InvestmentResearchReport) -> str:
        tickers = ", ".join(report.tickers()) or "None"
        return "\n".join(
            [
                (
                    '<h1 style="font-size: 28px; line-height: 1.2; margin: 0 0 '
                    '8px;">晨间投资报告</h1>'
                ),
                (
                    '<p style="margin: 0 0 18px; color: #4b5563;">'
                    f"{_html(report.title)} | 报告模式: {_html(report.mode.value)} "
                    f"| 生成时间: {_html(report.generated_at.isoformat())} "
                    f"| 标的: {_html(tickers)}</p>"
                ),
            ]
        )

    def _render_html_human_review_notice(self) -> str:
        return (
            '<p style="padding: 12px; background: #fff7ed; border-left: 4px solid '
            '#f97316; margin: 0 0 18px;">'
            "<strong>人工复核:</strong> 本报告仅提供研究和复核建议，不自动交易，"
            "也不代表已经或将会执行任何交易。</p>"
        )

    def _render_html_action_required(self, report: InvestmentResearchReport) -> str:
        items: list[str] = []
        for decision in self._html_action_decisions(report):
            review = (
                " 需要人工复核。"
                if decision.human_review_required
                else ""
            )
            items.append(
                "<li>"
                f"<strong>{_html(decision.symbol)}:</strong> "
                f"{_html(self._recommendation_label(decision.recommendation))} "
                f"(信心：{_html(self._localized_level(decision.confidence.value))}，"
                f"紧急程度：{_html(self._localized_level(decision.urgency.value))})。"
                f"{review}</li>"
            )
        if not items:
            items.append(
                "<li>当前没有需要处理的持仓决策。</li>"
            )
        if report.portfolio_decision_summary is not None:
            for item in report.portfolio_decision_summary.action_items:
                items.append(
                    f"<li><strong>组合待办：</strong> {_html(item)}</li>"
                )
        return "\n".join(
            [
                self._html_section_heading("1. 需要处理"),
                '<ul style="margin: 0 0 18px 20px; padding: 0;">',
                *items,
                "</ul>",
            ]
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
            opinions = self._committee_opinion_lookup(report)
            cards.extend(
                self._render_html_ticker_card(ticker_report, report, opinions)
                for ticker_report in report.ticker_reports
            )
        if not cards:
            cards.append(
                '<p style="margin: 0 0 18px;">暂无需要处理的持仓决策卡片。</p>'
            )
        return "\n".join([self._html_section_heading("2. 持仓决策卡片"), *cards])

    def _render_html_decision_card(self, decision: PositionDecision) -> str:
        recommendation = self._recommendation_label(decision.recommendation)
        badges = [
            self._html_badge(recommendation, kind="recommendation"),
            self._html_badge(
                f"信心：{self._localized_level(decision.confidence.value)}",
                kind="confidence",
            ),
            self._html_badge(
                f"紧急程度：{self._localized_level(decision.urgency.value)}",
                kind="urgency",
            ),
        ]
        if decision.human_review_required:
            badges.append(self._html_badge("需要人工复核", kind="review"))
        return self._html_card(
            title=f"{decision.symbol} - {recommendation}",
            border_color=self._recommendation_border_color(recommendation),
            body="\n".join(
                [
                    self._html_badge_row(badges),
                    self._html_field("建议", recommendation),
                    self._html_field(
                        "信心",
                        self._localized_level(decision.confidence.value),
                    ),
                    self._html_field(
                        "紧急程度",
                        self._localized_level(decision.urgency.value),
                    ),
                    self._html_field("理由", decision.final_rationale),
                    self._html_field(
                        "最终共识",
                        (
                            f"{decision.final_rationale} 不自动交易，"
                            "建议人工复核后再决定。"
                        ),
                    ),
                    self._render_html_actionable_sizing(decision),
                    self._html_field("东东", decision.dongdong_opinion),
                    self._html_field("西西", decision.xixi_opinion),
                    self._html_field("悠悠", decision.youyou_opinion),
                    self._html_details(
                        "事实依据",
                        [
                            self._html_field("东东", decision.dongdong_opinion),
                            self._html_field("西西", decision.xixi_opinion),
                            self._html_field("悠悠", decision.youyou_opinion),
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
        opinions: dict[str, str],
    ) -> str:
        recommendation = self._localized_recommendation_text(
            report.committee_consensus.final_action
        )
        badges = [
            self._html_badge(recommendation, kind="recommendation"),
            self._html_badge(
                (
                    "信心："
                    f"{self._localized_level(report.committee_consensus.confidence)}"
                ),
                kind="confidence",
            ),
            self._html_badge("需要人工复核", kind="review"),
        ]
        return self._html_card(
            title=f"{ticker_report.ticker} - {recommendation}",
            border_color=self._recommendation_border_color(recommendation),
            body="\n".join(
                [
                    self._html_badge_row(badges),
                    self._html_field("建议", recommendation),
                    self._html_field(
                        "信心",
                        self._localized_level(report.committee_consensus.confidence),
                    ),
                    self._html_field("理由", ticker_report.summary),
                    self._html_field(
                        "最终共识",
                        (
                            f"{report.committee_consensus.rationale} 不自动交易，"
                            "建议人工复核后再决定。"
                        ),
                    ),
                    self._html_field("东东", opinions.get("dongdong")),
                    self._html_field("西西", opinions.get("xixi")),
                    self._html_field("悠悠", opinions.get("youyou")),
                    self._html_details(
                        "事实依据",
                        [
                            self._html_field("东东", opinions.get("dongdong")),
                            self._html_field("西西", opinions.get("xixi")),
                            self._html_field("悠悠", opinions.get("youyou")),
                            self._html_list(
                                self._privacy_safe_values(
                                    self._ticker_evidence(ticker_report)
                                )
                            ),
                        ],
                    ),
                ]
            ),
        )

    def _render_html_stable_holdings(self, report: InvestmentResearchReport) -> str:
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
                f"(信心：{self._localized_level(decision.confidence.value)})。"
                f"{decision.final_rationale}"
            )
        if not items:
            for position in self._stable_portfolio_positions(report):
                items.append(f"{position.symbol}: 当前无需处理，敏感持仓数据已隐藏。")
        stable_symbols = {decision.symbol for decision in stable_decisions}
        if report.portfolio_decision_summary is not None:
            for symbol in report.portfolio_decision_summary.no_action_positions:
                if symbol not in stable_symbols:
                    items.append(f"{symbol}: 当前无需处理。")
        if not items:
            items.append("暂无稳定持仓信息。")
        return "\n".join(
            [
                self._html_section_heading("3. 稳定持仓"),
                self._html_details("查看稳定持仓", [self._html_list(items)]),
            ]
        )

    def _render_html_new_opportunities(self, report: InvestmentResearchReport) -> str:
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
                                        (
                                            "信心："
                                            f"{self._localized_level(opportunity.confidence.value)}"
                                        ),
                                        kind="confidence",
                                    ),
                                ]
                            ),
                            self._html_field("建议", recommendation),
                            self._html_field(
                                "信心",
                                self._localized_level(opportunity.confidence.value),
                            ),
                            self._html_field("理由", opportunity.rationale),
                            (
                                '<p style="margin: 8px 0 4px;">'
                                "<strong>风险:</strong></p>"
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
        return "\n".join([self._html_section_heading("4. 新机会"), *cards])

    def _render_html_market_overview(self, report: InvestmentResearchReport) -> str:
        items = [
            report.market_summary,
            f"组合背景：{report.portfolio_review}",
        ]
        if report.portfolio_decision_summary is not None:
            items.append(
                "组合观点："
                f"{report.portfolio_decision_summary.overall_portfolio_view}"
            )
            items.extend(
                f"集中度风险：{risk}"
                for risk in report.portfolio_decision_summary.concentration_risks
            )
            items.extend(
                f"行业暴露：{note}"
                for note in report.portfolio_decision_summary.sector_exposure_notes
            )
            items.extend(
                f"现金安排：{note}"
                for note in report.portfolio_decision_summary.cash_allocation_notes
            )
        return "\n".join(
            [
                self._html_section_heading("5. 市场概览"),
                self._html_list(self._privacy_safe_values(items)),
            ]
        )

    def _render_html_raw_evidence(self, report: InvestmentResearchReport) -> str:
        raw_lines = tuple(
            line.lstrip("- ").strip()
            for line in self._raw_evidence_lines(report)
        )
        evidence = self._privacy_safe_values(raw_lines) or ("暂无原始证据。",)
        return "\n".join(
            [
                self._html_section_heading("6. 原始证据"),
                self._html_details("查看原始证据", [self._html_list(evidence)]),
            ]
        )

    def _render_html_actionable_sizing(self, decision: PositionDecision) -> str:
        fields = [
            ("当前状态", self._current_status_label(decision)),
            ("建议动作", self._recommendation_label(decision.recommendation)),
            ("参考股数", self._share_guidance(decision)),
            ("目标仓位", self._target_weight_guidance(decision)),
            ("执行方式", "建议分批复核，不自动交易"),
        ]
        return "\n".join(
            [
                (
                    '<div style="background: #f8fafc; border: 1px solid #e2e8f0; '
                    'border-radius: 8px; padding: 10px; margin: 10px 0;">'
                ),
                '<p style="margin: 0 0 6px;"><strong>行动与仓位复核</strong></p>',
                *[self._html_field(label, value) for label, value in fields],
                "</div>",
            ]
        )

    def _current_status_label(self, decision: PositionDecision) -> str:
        if decision.recommendation is PositionRecommendation.SELL:
            return "风险偏高"
        if decision.recommendation is PositionRecommendation.TRIM:
            return "仓位偏高"
        return "仓位需要复核"

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
            return _format_share_guidance(explicit)
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
            return _format_share_guidance(numeric)
        return "具体股数需人工确认"

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
            return _format_weight_guidance(explicit)
        lower = getattr(decision, "target_weight_min", None)
        upper = getattr(decision, "target_weight_max", None)
        if lower is not None and upper is not None:
            return _format_weight_guidance((lower, upper))
        target = getattr(decision, "target_weight", None)
        if target is not None:
            return _format_weight_guidance(target)
        return "具体比例需人工确认"

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
                    '<details style="background: #ffffff; border: 1px solid #e5e7eb; '
                    f"border-left: 5px solid {border_color}; border-radius: 10px; "
                    'padding: 14px; margin: 12px 0;">'
                ),
                (
                    '<summary style="cursor: pointer; color: #111827; '
                    'font-weight: 800;">'
                    '<span style="font-size: 18px;">'
                    f"{_html(title)}</span></summary>"
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

    def _html_list(self, values: Iterable[str]) -> str:
        normalized = tuple(value.strip() for value in values if value.strip())
        items = normalized or ("暂无可用信息",)
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
        return {
            "high": "高",
            "medium": "中",
            "low": "低",
            "none": "无",
        }.get(str(value).strip().lower(), self._title_value(str(value)))

    def _recommendation_label(self, value: PositionRecommendation | str) -> str:
        recommendation = (
            value
            if isinstance(value, PositionRecommendation)
            else PositionRecommendation(str(value).strip().lower())
        )
        return {
            PositionRecommendation.BUY_MORE: "买入复核",
            PositionRecommendation.HOLD: "继续持有",
            PositionRecommendation.WATCH: "继续观察",
            PositionRecommendation.TRIM: "减仓复核",
            PositionRecommendation.SELL: "卖出复核",
            PositionRecommendation.NO_ACTION: "继续持有",
        }[recommendation]

    def _localized_recommendation_text(self, value: str) -> str:
        normalized = str(value).strip().lower().replace(" ", "_")
        if normalized == "buy":
            normalized = PositionRecommendation.BUY_MORE.value
        try:
            return self._recommendation_label(PositionRecommendation(normalized))
        except ValueError:
            return self._title_value(str(value))

    def _privacy_safe_values(self, values: Iterable[str]) -> tuple[str, ...]:
        return tuple(value for value in values if not _looks_portfolio_sensitive(value))


def _first_existing_attr(obj: object, names: Iterable[str]) -> object | None:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _format_share_guidance(value: object) -> str:
    if isinstance(value, tuple | list) and len(value) >= 2:
        lower = _coerce_positive_float(value[0])
        upper = _coerce_positive_float(value[1])
        if lower is not None and upper is not None:
            return _format_share_range(lower, upper)
    numeric = _coerce_positive_float(value)
    if numeric is None:
        return "具体股数需人工确认"
    lower, upper = _approximate_share_range(numeric)
    return _format_share_range(lower, upper)


def _format_share_range(lower: float, upper: float) -> str:
    low = max(1, int(round(min(lower, upper))))
    high = max(low, int(round(max(lower, upper))))
    return f"约 {low:g}–{high:g} 股"


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


def _format_weight_guidance(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        return text or "具体比例需人工确认"
    if isinstance(value, tuple | list) and len(value) >= 2:
        lower = _coerce_positive_float(value[0])
        upper = _coerce_positive_float(value[1])
        if lower is not None and upper is not None:
            return f"目标仓位 {_format_percent(lower)}–{_format_percent(upper)}"
    numeric = _coerce_positive_float(value)
    if numeric is not None:
        return f"目标仓位 {_format_percent(numeric)}"
    return "具体比例需人工确认"


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
    )
    return any(term in normalized for term in sensitive_terms)


def _format_money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${float(value):,.2f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{float(value) * 100:.1f}%"


def render_investment_research_report(report: InvestmentResearchReport) -> str:
    """Render an investment research report as plain text."""
    return InvestmentResearchReportRenderer().render(report)


def render_investment_research_report_interactive_html_email(
    report: InvestmentResearchReport,
) -> str:
    """Render an investment research report as standalone HTML email."""
    return InteractiveHtmlEmailInvestmentResearchReportRenderer().render(report)


def _html(value: Any) -> str:
    return escape(str(value), quote=True)


__all__ = [
    "InteractiveHtmlEmailInvestmentResearchReportRenderer",
    "InvestmentResearchReportRenderer",
    "render_investment_research_report",
    "render_investment_research_report_interactive_html_email",
]
