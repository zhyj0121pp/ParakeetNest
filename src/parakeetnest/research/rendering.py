"""Plain-text rendering for investment research reports."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any

from parakeetnest.research.models import (
    InvestmentResearchReport,
    ResearchCatalyst,
    ResearchFinding,
    ResearchRecommendation,
    ResearchRisk,
    ResearchTickerReport,
)


class InvestmentResearchReportRenderer:
    """Render research reports into deterministic plain-text email bodies."""

    def render(self, report: InvestmentResearchReport) -> str:
        """Return a plain-text report suitable for an email body."""
        sections = [
            self._render_header(report),
            self._render_market_summary(report),
            self._render_portfolio_review(report),
            self._render_watchlist_review(report),
            self._render_executive_summary(report),
            self._render_committee_opinions(report),
            self._render_committee_consensus(report),
            self._render_confidence(report),
            self._render_ticker_reports(report.ticker_reports),
            self._render_recommendations(report.ticker_reports),
            self._render_key_risks(report.ticker_reports),
            self._render_upcoming_catalysts(report.ticker_reports),
            self._render_todays_suggested_actions(report),
            self._render_evidence_notes(report),
        ]
        return "\n\n".join(section.rstrip() for section in sections).rstrip() + "\n"

    def _render_header(self, report: InvestmentResearchReport) -> str:
        tickers = ", ".join(report.tickers()) or "None"
        return "\n".join(
            [
                "Header",
                report.title,
                f"Generated At: {report.generated_at.isoformat()}",
                f"Tickers: {tickers}",
            ]
        )

    def _render_market_summary(self, report: InvestmentResearchReport) -> str:
        return "\n".join(["Market Summary", f"- {report.market_summary}"])

    def _render_portfolio_review(self, report: InvestmentResearchReport) -> str:
        return "\n".join(["Portfolio Review", f"- {report.portfolio_review}"])

    def _render_watchlist_review(self, report: InvestmentResearchReport) -> str:
        return "\n".join(["Watchlist Review", f"- {report.watchlist_review}"])

    def _render_executive_summary(self, report: InvestmentResearchReport) -> str:
        lines = ["Executive Summary"]
        if not report.ticker_reports:
            lines.append("- No ticker reports were generated.")
            return "\n".join(lines)

        action_counts: dict[str, int] = {}
        for ticker_report in report.ticker_reports:
            action = self._value(ticker_report.recommendation.action).upper()
            action_counts[action] = action_counts.get(action, 0) + 1
        action_summary = ", ".join(
            f"{action}: {count}" for action, count in sorted(action_counts.items())
        )
        lines.append(f"- Coverage: {len(report.ticker_reports)} ticker(s).")
        lines.append(f"- Actions: {action_summary}.")
        for ticker_report in report.ticker_reports:
            recommendation = ticker_report.recommendation
            lines.append(
                "- "
                f"{ticker_report.ticker}: {self._value(recommendation.action).upper()} "
                f"({self._value(recommendation.confidence)} confidence) - "
                f"{ticker_report.summary}"
            )
        return "\n".join(lines)

    def _render_committee_opinions(self, report: InvestmentResearchReport) -> str:
        lines = ["Committee Opinions"]
        for opinion in report.committee_opinions:
            lines.extend(
                [
                    f"{opinion.display_name}'s Opinion ({opinion.role_title})",
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
        return "\n".join(["Committee Consensus", f"- {report.committee_consensus}"])

    def _render_confidence(self, report: InvestmentResearchReport) -> str:
        lines = ["Confidence"]
        for ticker_report in report.ticker_reports:
            lines.append(
                "- "
                f"{ticker_report.ticker}: "
                f"{self._value(ticker_report.recommendation.confidence)}"
            )
        if len(lines) == 1:
            lines.append("- No confidence levels.")
        return "\n".join(lines)

    def _render_ticker_reports(
        self,
        ticker_reports: Iterable[ResearchTickerReport],
    ) -> str:
        lines = ["Ticker Reports"]
        for ticker_report in ticker_reports:
            recommendation = ticker_report.recommendation
            lines.extend(
                [
                    f"- {ticker_report.ticker}",
                    f"  Summary: {ticker_report.summary}",
                    "  Recommendation: "
                    f"{self._value(recommendation.action).upper()} | "
                    f"confidence {self._value(recommendation.confidence)} | "
                    f"horizon {recommendation.horizon}",
                ]
            )
            if recommendation.rationale:
                lines.append(f"  Rationale: {recommendation.rationale}")
            lines.extend(self._render_values("Bull Case", ticker_report.bull_case))
            lines.extend(self._render_values("Bear Case", ticker_report.bear_case))
            lines.extend(self._render_findings(ticker_report.findings))
            lines.extend(self._render_values("Sources", ticker_report.source_summaries))
        if len(lines) == 1:
            lines.append("- No ticker reports.")
        return "\n".join(lines)

    def _render_recommendations(
        self,
        ticker_reports: Iterable[ResearchTickerReport],
    ) -> str:
        lines = ["Recommendations"]
        for ticker_report in ticker_reports:
            recommendation = ticker_report.recommendation
            lines.append(
                "- "
                f"{ticker_report.ticker}: {self._value(recommendation.action).upper()} "
                f"| confidence {self._value(recommendation.confidence)} "
                f"| horizon {recommendation.horizon}"
            )
            lines.extend(self._render_recommendation_detail(recommendation))
        if len(lines) == 1:
            lines.append("- No recommendations.")
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
        lines.extend(f"- {action}" for action in report.todays_suggested_actions)
        if len(lines) == 1:
            lines.append("- No suggested actions.")
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

    def _render_recommendation_detail(
        self,
        recommendation: ResearchRecommendation,
    ) -> list[str]:
        lines: list[str] = []
        lines.extend(self._render_values("Evidence", recommendation.evidence))
        lines.extend(self._render_values("Risks", recommendation.risks))
        lines.extend(self._render_values("Catalysts", recommendation.catalysts))
        if recommendation.rationale:
            lines.append(f"  Rationale: {recommendation.rationale}")
        return lines

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
