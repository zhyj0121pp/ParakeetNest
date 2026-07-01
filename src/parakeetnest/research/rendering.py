"""Plain-text rendering for investment research reports."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any

from parakeetnest.research.models import (
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
)


class InvestmentResearchReportRenderer:
    """Render research reports into deterministic plain-text email bodies."""

    def render(self, report: InvestmentResearchReport) -> str:
        """Return a plain-text report suitable for an email body."""
        if report.mode is ReportMode.EVENING:
            sections = self._render_evening_sections(report)
        else:
            sections = self._render_morning_sections(report)
        return "\n\n".join(section.rstrip() for section in sections).rstrip() + "\n"

    def _render_morning_sections(self, report: InvestmentResearchReport) -> list[str]:
        return [
            self._render_header(report),
            self._render_market_summary(report, label="Market Setup"),
            self._render_portfolio_review(report, label="Portfolio Watch"),
            self._render_watchlist_review(report, label="Watchlist Focus"),
            self._render_focus(report, label="Today’s Focus"),
            self._render_ticker_reports(report.ticker_reports),
            self._render_committee_opinions(
                report,
                labels={
                    "dongdong": "Dongdong’s Opportunity View",
                    "xixi": "Xixi’s Fundamental View",
                    "youyou": "Youyou’s Risk View",
                },
            ),
            self._render_committee_consensus(report),
            self._render_confidence(report),
            self._render_key_risks(report.ticker_reports),
            self._render_upcoming_catalysts(report.ticker_reports),
            self._render_todays_suggested_actions(report),
            self._render_evidence_notes(report),
        ]

    def _render_evening_sections(self, report: InvestmentResearchReport) -> list[str]:
        sections = [
            self._render_header(report),
            self._render_market_summary(report, label="Market Recap"),
            self._render_portfolio_review(report, label="Portfolio Review"),
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


def render_investment_research_report(report: InvestmentResearchReport) -> str:
    """Render an investment research report as plain text."""
    return InvestmentResearchReportRenderer().render(report)


__all__ = [
    "InvestmentResearchReportRenderer",
    "render_investment_research_report",
]
