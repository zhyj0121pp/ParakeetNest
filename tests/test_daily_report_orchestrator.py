"""Tests for daily report workflow orchestration."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from parakeetnest.reports import (
    DailyReportOrchestrator,
    DailyReportRequest,
)
from parakeetnest.research import ReportMode


AS_OF_DATE = date(2026, 7, 1)


class RecordingComposer:
    def __init__(self, body: str = "daily report body\n") -> None:
        self.body = body
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        tickers: tuple[str, ...],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> str:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "mode": mode,
            }
        )
        return self.body


class RecordingEmailService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def send(
        self,
        report: str,
        *,
        recipient: str,
        as_of_date: date | None = None,
        mode: ReportMode | str | None = None,
    ) -> None:
        self.calls.append(
            {
                "report": report,
                "recipient": recipient,
                "as_of_date": as_of_date,
                "mode": mode,
            }
        )


def test_orchestrator_generates_report_only(tmp_path: Path) -> None:
    composer = RecordingComposer()
    orchestrator = DailyReportOrchestrator(composer=composer)

    result = orchestrator.run(
        DailyReportRequest(
            mode=ReportMode.MORNING,
            tickers=("NVDA",),
            account_id="main",
            as_of_date=AS_OF_DATE,
        )
    )

    assert result.body == "daily report body\n"
    assert result.archive_path is None
    assert result.output_path is None
    assert result.email_sent is False
    assert composer.calls == [
        {
            "tickers": ("NVDA",),
            "account_id": "main",
            "as_of_date": AS_OF_DATE,
            "mode": ReportMode.MORNING,
        }
    ]
    assert not (tmp_path / "reports").exists()


def test_orchestrator_archives_when_requested(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    orchestrator = DailyReportOrchestrator(composer=RecordingComposer())

    result = orchestrator.run(
        DailyReportRequest(
            mode=ReportMode.MORNING,
            tickers=("NVDA",),
            as_of_date=AS_OF_DATE,
            archive=True,
        )
    )

    archive_path = (
        tmp_path
        / "reports"
        / "2026-07-01"
        / "morning-investment-brief.md"
    )
    assert result.archive_path == Path("reports/2026-07-01/morning-investment-brief.md")
    assert archive_path.read_text(encoding="utf-8") == "daily report body\n"


def test_orchestrator_writes_explicit_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "custom" / "daily-report.md"
    orchestrator = DailyReportOrchestrator(composer=RecordingComposer())

    result = orchestrator.run(
        DailyReportRequest(
            mode=ReportMode.MORNING,
            tickers=("NVDA",),
            output_path=output_path,
        )
    )

    assert result.output_path == output_path
    assert result.archive_path is None
    assert output_path.read_text(encoding="utf-8") == "daily report body\n"


def test_orchestrator_writes_both_archive_and_output_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "custom" / "daily-report.md"
    orchestrator = DailyReportOrchestrator(composer=RecordingComposer())

    result = orchestrator.run(
        DailyReportRequest(
            mode=ReportMode.EVENING,
            tickers=("NVDA",),
            as_of_date=AS_OF_DATE,
            archive=True,
            output_path=output_path,
        )
    )

    archive_path = (
        tmp_path
        / "reports"
        / "2026-07-01"
        / "evening-investment-review.md"
    )
    assert result.output_path == output_path
    assert result.archive_path == Path("reports/2026-07-01/evening-investment-review.md")
    assert output_path.read_text(encoding="utf-8") == "daily report body\n"
    assert archive_path.read_text(encoding="utf-8") == "daily report body\n"


def test_orchestrator_sends_email_when_recipient_exists() -> None:
    email_service = RecordingEmailService()
    orchestrator = DailyReportOrchestrator(
        composer=RecordingComposer("Market Summary\n"),
        email_service=email_service,
    )

    result = orchestrator.run(
        DailyReportRequest(
            mode=ReportMode.EVENING,
            tickers=("NVDA",),
            as_of_date=AS_OF_DATE,
            email_recipient="investor@example.com",
        )
    )

    assert result.email_sent is True
    assert email_service.calls == [
        {
            "report": "Market Summary\n",
            "recipient": "investor@example.com",
            "as_of_date": AS_OF_DATE,
            "mode": ReportMode.EVENING,
        }
    ]


def test_orchestrator_contains_no_scheduler_logic() -> None:
    source = Path("src/parakeetnest/reports/daily_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "scheduler" not in source.lower()
