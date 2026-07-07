"""Workflow orchestration for local daily investment reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping, Protocol

from parakeetnest.research import (
    DailyInvestmentReportComposer,
    ReportDeliveryAttachment,
    ReportDeliveryResult,
    ReportBodyFormat,
    ReportMode,
)
from parakeetnest.research.localization import ReportLanguage, get_report_localization


class _ReportDeliveryService(Protocol):
    def deliver_report(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        content_type: str = "text/plain",
        metadata: Mapping[str, str] | None = None,
        attachments: tuple[ReportDeliveryAttachment, ...] | None = None,
    ) -> ReportDeliveryResult:
        """Deliver a prepared report body."""


DEFAULT_OUTPUT_PATH = Path("reports/daily-report.html")
DEFAULT_ARCHIVE_ROOT = Path("reports")
ARCHIVE_FILENAMES = {
    ReportMode.MORNING: "morning-investment-brief.html",
    ReportMode.EVENING: "evening-investment-review.html",
}


@dataclass(frozen=True)
class DailyReportRequest:
    """Inputs for one daily report workflow run."""

    mode: ReportMode | str
    tickers: tuple[str, ...]
    account_id: str | None = None
    as_of_date: date | None = None
    archive: bool = False
    output_path: Path | None = None
    email_recipient: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ReportMode.from_value(self.mode))
        object.__setattr__(self, "tickers", tuple(self.tickers))


@dataclass(frozen=True)
class DailyReportResult:
    """Outputs from one daily report workflow run."""

    body: str
    archive_path: Path | None = None
    output_path: Path | None = None
    email_sent: bool = False


class DailyReportOrchestrator:
    """Coordinate report generation, optional persistence, and optional email."""

    def __init__(
        self,
        *,
        composer: DailyInvestmentReportComposer | None = None,
        delivery_service: _ReportDeliveryService | None = None,
    ) -> None:
        self._composer = composer or DailyInvestmentReportComposer()
        self._delivery_service = delivery_service

    def run(self, request: DailyReportRequest) -> DailyReportResult:
        """Run the daily report workflow."""
        body = generate_daily_report(
            request.tickers,
            account_id=request.account_id,
            as_of_date=request.as_of_date,
            mode=request.mode,
            composer=self._composer,
        )

        output_path = None
        if request.output_path is not None:
            output_path = write_daily_report_body(body, request.output_path)

        archive_path = None
        if request.archive:
            archive_path = write_daily_report_body(
                body,
                build_archive_output_path(
                    mode=request.mode,
                    as_of_date=request.as_of_date,
                ),
            )

        email_sent = False
        if request.email_recipient:
            if self._delivery_service is None:
                raise ValueError(
                    "delivery service is required when email_recipient is set"
                )
            deliver_daily_report_attachment(
                delivery_service=self._delivery_service,
                recipient_email=request.email_recipient,
                html_report=body,
                as_of_date=request.as_of_date,
            )
            email_sent = True

        return DailyReportResult(
            body=body,
            archive_path=archive_path,
            output_path=output_path,
            email_sent=email_sent,
        )


def generate_daily_report(
    tickers: tuple[str, ...],
    *,
    account_id: str | None = None,
    as_of_date: date | None = None,
    mode: ReportMode | str = ReportMode.MORNING,
    composer: DailyInvestmentReportComposer | None = None,
    body_format: ReportBodyFormat | str = ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
) -> str:
    """Generate a daily report body."""
    report_composer = composer or DailyInvestmentReportComposer()
    return report_composer.compose(
        tickers,
        account_id=account_id,
        as_of_date=as_of_date,
        mode=mode,
        body_format=body_format,
    )


def write_daily_report(
    tickers: tuple[str, ...],
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    account_id: str | None = None,
    as_of_date: date | None = None,
    mode: ReportMode | str = ReportMode.MORNING,
    composer: DailyInvestmentReportComposer | None = None,
) -> Path:
    """Generate a daily report body and write it to a local file."""
    body = generate_daily_report(
        tickers,
        account_id=account_id,
        as_of_date=as_of_date,
        mode=mode,
        composer=composer,
    )
    return write_daily_report_body(body, output_path)


def write_daily_report_body(body: str, output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    """Write a generated daily report body to a local file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path


def deliver_daily_report_attachment(
    *,
    delivery_service: _ReportDeliveryService,
    recipient_email: str,
    html_report: str,
    as_of_date: date | None = None,
) -> ReportDeliveryResult:
    """Deliver a generated daily report as a text email plus HTML attachment."""
    report_date = as_of_date or date.today()
    localization = get_report_localization()
    filename = f"morning-report-{report_date.isoformat()}.html"
    return delivery_service.deliver_report(
        recipient_email=recipient_email,
        subject=f"{localization.report_title} - {report_date.isoformat()}",
        body=_minimal_attachment_body(
            title=localization.report_title,
            report_date=report_date,
            attachment_filename=filename,
            language=localization.language,
        ),
        content_type=ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT.content_type,
        attachments=(
            ReportDeliveryAttachment(
                filename=filename,
                content=html_report,
                content_type="text/html",
            ),
        ),
    )


def _minimal_attachment_body(
    *,
    title: str,
    report_date: date,
    attachment_filename: str,
    language: ReportLanguage,
) -> str:
    if language is ReportLanguage.ZH:
        return (
            f"{title}\n"
            f"日期：{report_date.isoformat()}\n"
            f"完整报告请查看附件：{attachment_filename}\n"
        )
    return (
        f"{title}\n"
        f"Date: {report_date.isoformat()}\n"
        f"Full report is attached: {attachment_filename}\n"
    )


def build_archive_output_path(
    *,
    mode: ReportMode | str,
    as_of_date: date | None = None,
    archive_root: Path = DEFAULT_ARCHIVE_ROOT,
) -> Path:
    """Build the conventional local archive path for a daily report."""
    report_mode = ReportMode.from_value(mode)
    report_date = as_of_date or date.today()
    return archive_root / report_date.isoformat() / ARCHIVE_FILENAMES[report_mode]
