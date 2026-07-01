"""Application-level composition for daily investment research reports."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from parakeetnest.research.models import InvestmentResearchReport
from parakeetnest.research.rendering import InvestmentResearchReportRenderer
from parakeetnest.research.service import InvestmentResearchService


class _ResearchService(Protocol):
    def generate_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> InvestmentResearchReport:
        """Generate a research report for requested tickers."""


class _ResearchReportRenderer(Protocol):
    def render(self, report: InvestmentResearchReport) -> str:
        """Render a research report into a plain-text body."""


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
    ) -> str:
        """Generate and render a plain-text daily investment report body."""
        report = self.compose_report(
            tickers,
            account_id=account_id,
            as_of_date=as_of_date,
            generated_at=generated_at,
        )
        return self._renderer.render(report)

    def compose_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> InvestmentResearchReport:
        """Generate the research report before delivery-specific rendering."""
        return self._research_service.generate_report(
            tickers,
            account_id=account_id,
            as_of_date=as_of_date,
            generated_at=generated_at,
        )


def compose_daily_investment_report(
    tickers: tuple[str, ...] | list[str],
    *,
    account_id: str | None = None,
    as_of_date: date | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Compose a plain-text daily investment report body."""
    return DailyInvestmentReportComposer().compose(
        tickers,
        account_id=account_id,
        as_of_date=as_of_date,
        generated_at=generated_at,
    )


__all__ = [
    "DailyInvestmentReportComposer",
    "compose_daily_investment_report",
]
