"""Tests for scheduler job wrappers."""

from __future__ import annotations

from parakeetnest.reports import DailyReportRequest, DailyReportResult
from parakeetnest.research import ReportMode
from parakeetnest.scheduler import DailyReportScheduledJob


class RecordingDailyReportOrchestrator:
    def __init__(self, result: DailyReportResult) -> None:
        self.result = result
        self.requests: list[DailyReportRequest] = []

    def run(self, request: DailyReportRequest) -> DailyReportResult:
        self.requests.append(request)
        return self.result


def test_daily_report_scheduled_job_calls_orchestrator() -> None:
    result = DailyReportResult(body="scheduled body\n")
    orchestrator = RecordingDailyReportOrchestrator(result)
    request = DailyReportRequest(mode=ReportMode.MORNING, tickers=("NVDA",))
    job = DailyReportScheduledJob(orchestrator=orchestrator, request=request)

    job.run()

    assert orchestrator.requests == [request]


def test_daily_report_scheduled_job_returns_daily_report_result() -> None:
    result = DailyReportResult(body="scheduled body\n")
    orchestrator = RecordingDailyReportOrchestrator(result)
    request = DailyReportRequest(mode=ReportMode.EVENING, tickers=("NVDA",))
    job = DailyReportScheduledJob(orchestrator=orchestrator, request=request)

    returned = job.run()

    assert returned is result
