"""Application-level composition for daily investment research reports."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from parakeetnest.research.models import InvestmentResearchReport, ReportMode
from parakeetnest.research.rendering import (
    InteractiveHtmlEmailInvestmentResearchReportRenderer,
    InvestmentResearchReportRenderer,
)
from parakeetnest.research.service import InvestmentResearchService


class _ResearchService(Protocol):
    def generate_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> InvestmentResearchReport:
        """Generate a research report for requested tickers."""


class _ResearchReportRenderer(Protocol):
    def render(self, report: InvestmentResearchReport) -> str:
        """Render a research report into a delivery body."""


class ReportBodyFormat(StrEnum):
    """Supported daily report body formats."""

    MARKDOWN = "markdown"
    INTERACTIVE_HTML_EMAIL = "interactive_html_email"
    INTERACTIVE_HTML_ATTACHMENT = "interactive_html_attachment"

    @property
    def content_type(self) -> str:
        """Return the MIME content type for this report body format."""
        if self is ReportBodyFormat.INTERACTIVE_HTML_EMAIL:
            return "text/html"
        return "text/plain"

    @classmethod
    def from_value(cls, value: ReportBodyFormat | str) -> ReportBodyFormat:
        """Normalize a report body format value."""
        if isinstance(value, cls):
            return value
        return cls(str(value).strip().lower())


class DailyInvestmentReportComposer:
    """Compose daily investment report bodies from research and rendering services."""

    def __init__(
        self,
        *,
        research_service: _ResearchService | None = None,
        renderer: _ResearchReportRenderer | None = None,
    ) -> None:
        self._research_service = research_service or InvestmentResearchService()
        self._renderer = renderer or InvestmentResearchReportRenderer()

    def compose(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
        body_format: ReportBodyFormat | str = ReportBodyFormat.MARKDOWN,
    ) -> str:
        """Generate and render a daily investment report body."""
        report = self.compose_report(
            tickers,
            account_id=account_id,
            as_of_date=as_of_date,
            generated_at=generated_at,
            mode=mode,
        )
        return self._renderer_for(body_format).render(report)

    def compose_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> InvestmentResearchReport:
        """Generate the research report before delivery-specific rendering."""
        return self._research_service.generate_report(
            tickers,
            account_id=account_id,
            as_of_date=as_of_date,
            generated_at=generated_at,
            mode=mode,
        )

    def _renderer_for(
        self,
        body_format: ReportBodyFormat | str,
    ) -> _ResearchReportRenderer:
        normalized_format = ReportBodyFormat.from_value(body_format)
        if normalized_format in {
            ReportBodyFormat.INTERACTIVE_HTML_EMAIL,
            ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
        }:
            return InteractiveHtmlEmailInvestmentResearchReportRenderer()
        return self._renderer


def compose_daily_investment_report(
    tickers: tuple[str, ...] | list[str],
    *,
    account_id: str | None = None,
    as_of_date: date | None = None,
    generated_at: datetime | None = None,
    mode: ReportMode | str = ReportMode.MORNING,
    body_format: ReportBodyFormat | str = ReportBodyFormat.MARKDOWN,
) -> str:
    """Compose a daily investment report body."""
    return DailyInvestmentReportComposer().compose(
        tickers,
        account_id=account_id,
        as_of_date=as_of_date,
        generated_at=generated_at,
        mode=mode,
        body_format=body_format,
    )


__all__ = [
    "DailyInvestmentReportComposer",
    "ReportBodyFormat",
    "compose_daily_investment_report",
]
