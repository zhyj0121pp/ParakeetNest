"""Tests for the manual scheduled daily report CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from parakeetnest.cli import scheduled_daily_report
from parakeetnest.reports import DailyReportResult
from parakeetnest.research import ReportMode


class EmptyWatchlistService:
    def build_all_insights(self) -> tuple[object, ...]:
        return ()


class RecordingApp:
    def __init__(self) -> None:
        self.watchlist_intelligence_service = EmptyWatchlistService()
        self.closed = False

    def close(self) -> None:
        self.closed = True


@dataclass(frozen=True)
class RecordingOrchestrator:
    name: str = "recording"


class RecordingScheduledJob:
    calls: list[dict[str, object]] = []

    def __init__(self, *, orchestrator: object, request: object) -> None:
        self.orchestrator = orchestrator
        self.request = request
        self.calls.append({"orchestrator": orchestrator, "request": request})

    def run(self) -> DailyReportResult:
        return DailyReportResult(body="scheduled body\n")


@pytest.fixture(autouse=True)
def scheduled_cli_fakes(monkeypatch: pytest.MonkeyPatch) -> RecordingApp:
    app = RecordingApp()
    RecordingScheduledJob.calls = []
    monkeypatch.setattr(
        scheduled_daily_report.daily_report,
        "create_app",
        lambda config: app,
    )
    monkeypatch.setattr(
        scheduled_daily_report.daily_report,
        "build_daily_report_orchestrator",
        lambda args, app, email_output: RecordingOrchestrator(),
    )
    monkeypatch.setattr(
        scheduled_daily_report,
        "DailyReportScheduledJob",
        RecordingScheduledJob,
    )
    return app


def test_scheduler_cli_supports_morning(
    capsys: pytest.CaptureFixture[str],
    scheduled_cli_fakes: RecordingApp,
) -> None:
    exit_code = scheduled_daily_report.main(
        ["--mode", "morning", "--tickers", "NVDA"]
    )

    request = RecordingScheduledJob.calls[0]["request"]
    assert exit_code == 0
    assert capsys.readouterr().out == "scheduled body\n"
    assert request.mode is ReportMode.MORNING
    assert scheduled_cli_fakes.closed is True


def test_scheduler_cli_supports_evening(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = scheduled_daily_report.main(
        ["--mode", "evening", "--tickers", "NVDA"]
    )

    request = RecordingScheduledJob.calls[0]["request"]
    assert exit_code == 0
    assert capsys.readouterr().out == "scheduled body\n"
    assert request.mode is ReportMode.EVENING


def test_scheduler_cli_passes_archive_output_email_options_into_request(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "scheduled.md"

    exit_code = scheduled_daily_report.main(
        [
            "--mode",
            "evening",
            "--tickers",
            "nvda",
            "--archive",
            "--output",
            str(output_path),
            "--email",
            "investor@example.com",
            "--as-of-date",
            "2026-07-01",
            "--account-id",
            "main",
        ]
    )

    request = RecordingScheduledJob.calls[0]["request"]
    assert exit_code == 0
    assert capsys.readouterr().out == "scheduled body\n"
    assert request.mode is ReportMode.EVENING
    assert request.tickers == ("NVDA",)
    assert request.archive is True
    assert request.output_path == output_path
    assert request.email_recipient == "investor@example.com"
    assert request.as_of_date == date(2026, 7, 1)
    assert request.account_id == "main"


def test_scheduler_cli_uses_scheduled_job() -> None:
    exit_code = scheduled_daily_report.main(["--tickers", "NVDA"])

    assert exit_code == 0
    assert RecordingScheduledJob.calls == [
        {
            "orchestrator": RecordingOrchestrator(),
            "request": RecordingScheduledJob.calls[0]["request"],
        }
    ]


def test_scheduler_cli_has_no_gmail_imports() -> None:
    source = Path("src/parakeetnest/cli/scheduled_daily_report.py").read_text(
        encoding="utf-8"
    )
    job_source = Path("src/parakeetnest/scheduler/jobs.py").read_text(
        encoding="utf-8"
    )

    assert "gmail" not in source.lower()
    assert "gmail" not in job_source.lower()


def test_project_adds_no_cron_or_cloud_dependencies() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8").lower()

    assert "apscheduler" not in pyproject
    assert "croniter" not in pyproject
    assert "google-cloud" not in pyproject
    assert "boto3" not in pyproject
