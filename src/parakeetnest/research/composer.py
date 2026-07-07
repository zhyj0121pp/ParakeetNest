"""Application-level composition for daily investment research reports."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from parakeetnest.research.models import InvestmentResearchReport, ReportMode
from parakeetnest.research.rendering import (
    InteractiveHtmlInvestmentResearchReportRenderer,
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

    INTERACTIVE_HTML_ATTACHMENT = "interactive_html_attachment"

    @property
    def content_type(self) -> str:
        """Return the MIME content type for this report body format."""
        return "text/plain"

    @classmethod
    def from_value(cls, value: ReportBodyFormat | str) -> ReportBodyFormat:
        """Normalize a report body format value."""
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        if normalized != cls.INTERACTIVE_HTML_ATTACHMENT:
            raise ValueError(f"{normalized!r} is not a valid ReportBodyFormat")
        return cls.INTERACTIVE_HTML_ATTACHMENT


class DailyInvestmentReportComposer:
    """Compose daily investment report bodies from research and rendering services."""

    def __init__(
        self,
        *,
        research_service: _ResearchService | None = None,
        renderer: _ResearchReportRenderer | None = None,
    ) -> None:
        self._research_service = research_service or InvestmentResearchService()
        self._renderer = renderer or InteractiveHtmlInvestmentResearchReportRenderer()

    def compose(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
        body_format: ReportBodyFormat | str = (
            ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT
        ),
    ) -> str:
        """Generate and render a daily investment report body."""
        report = self.compose_report(
            tickers,
            account_id=account_id,
            as_of_date=as_of_date,
            generated_at=generated_at,
            mode=mode,
        )
        ReportBodyFormat.from_value(body_format)
        return self._renderer.render(report)

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

def compose_daily_investment_report(
    tickers: tuple[str, ...] | list[str],
    *,
    account_id: str | None = None,
    as_of_date: date | None = None,
    generated_at: datetime | None = None,
    mode: ReportMode | str = ReportMode.MORNING,
    body_format: ReportBodyFormat | str = (
        ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT
    ),
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
