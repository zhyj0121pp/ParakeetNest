"""Scheduler job definitions."""

from __future__ import annotations

from parakeetnest.reports import (
    DailyReportOrchestrator,
    DailyReportRequest,
    DailyReportResult,
)


class DailyReportScheduledJob:
    """Scheduler-compatible wrapper for one daily report workflow run."""

    def __init__(
        self,
        *,
        orchestrator: DailyReportOrchestrator,
        request: DailyReportRequest,
    ) -> None:
        self._orchestrator = orchestrator
        self._request = request

    def run(self) -> DailyReportResult:
        """Trigger the daily report orchestrator."""
        return self._orchestrator.run(self._request)
