"""Email-friendly Markdown rendering for investment research reports."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
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


__all__ = [
    "InvestmentResearchReportRenderer",
    "render_investment_research_report",
]
