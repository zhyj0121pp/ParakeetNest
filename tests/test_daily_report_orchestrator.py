"""Tests for daily report workflow orchestration."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from parakeetnest.reports import (
    DailyReportOrchestrator,
    DailyReportRequest,
)
from parakeetnest.config import get_settings
from parakeetnest.research import ReportBodyFormat, ReportMode


AS_OF_DATE = date(2026, 7, 1)


class RecordingComposer:
    def __init__(
        self,
        body: str = "legacy report body\n",
        html_body: str = "<!doctype html>\n<html></html>\n",
    ) -> None:
        self.body = body
        self.html_body = html_body
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        tickers: tuple[str, ...],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
        body_format: ReportBodyFormat | str = (
            ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT
        ),
    ) -> str:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "mode": mode,
                "body_format": body_format,
            }
        )
        if body_format is ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT:
            return self.html_body
        return self.body


class RecordingDeliveryService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def deliver_report(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        content_type: str = "text/plain",
        metadata: object | None = None,
        attachments: tuple[object, ...] | None = None,
    ) -> None:
        self.calls.append(
            {
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "content_type": content_type,
                "metadata": metadata,
                "attachments": attachments or (),
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

    assert result.body == "<!doctype html>\n<html></html>\n"
    assert result.archive_path is None
    assert result.output_path is None
    assert result.email_sent is False
    assert composer.calls == [
        {
            "tickers": ("NVDA",),
            "account_id": "main",
            "as_of_date": AS_OF_DATE,
            "mode": ReportMode.MORNING,
            "body_format": ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
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
        / "morning-investment-brief.html"
    )
    assert result.archive_path == Path(
        "reports/2026-07-01/morning-investment-brief.html"
    )
    assert archive_path.read_text(encoding="utf-8") == "<!doctype html>\n<html></html>\n"


def test_orchestrator_writes_explicit_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "custom" / "daily-report.html"
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
    assert output_path.read_text(encoding="utf-8") == "<!doctype html>\n<html></html>\n"


def test_orchestrator_writes_both_archive_and_output_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "custom" / "daily-report.html"
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
        / "evening-investment-review.html"
    )
    assert result.output_path == output_path
    assert result.archive_path == Path(
        "reports/2026-07-01/evening-investment-review.html"
    )
    assert output_path.read_text(encoding="utf-8") == "<!doctype html>\n<html></html>\n"
    assert archive_path.read_text(encoding="utf-8") == "<!doctype html>\n<html></html>\n"


def test_orchestrator_sends_email_when_recipient_exists(monkeypatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_service = RecordingDeliveryService()
    orchestrator = DailyReportOrchestrator(
        composer=RecordingComposer(
            "Market Summary\n",
            html_body="<!doctype html>\n<html><body>Market Summary</body></html>\n",
        ),
        delivery_service=delivery_service,
    )

    try:
        result = orchestrator.run(
            DailyReportRequest(
                mode=ReportMode.EVENING,
                tickers=("NVDA",),
                as_of_date=AS_OF_DATE,
                email_recipient="investor@example.com",
            )
        )
    finally:
        get_settings.cache_clear()

    assert result.email_sent is True
    assert len(delivery_service.calls) == 1
    call = delivery_service.calls[0]
    assert call["recipient_email"] == "investor@example.com"
    assert call["subject"] == "Morning Investment Report - 2026-07-01"
    assert call["body"] == (
        "Morning Investment Report\n"
        "Date: 2026-07-01\n"
        "Full report is attached: morning-report-2026-07-01.html\n"
    )
    assert call["content_type"] == "text/plain"
    attachment = call["attachments"][0]
    assert attachment.filename == "morning-report-2026-07-01.html"
    assert attachment.content == "<!doctype html>\n<html><body>Market Summary</body></html>"
    assert attachment.content_type == "text/html"


def test_orchestrator_contains_no_scheduler_logic() -> None:
    source = Path("src/parakeetnest/reports/daily_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "scheduler" not in source.lower()
