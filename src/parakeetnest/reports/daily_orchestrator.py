"""Workflow orchestration for local daily investment reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from parakeetnest.email import EmailService
from parakeetnest.research import (
    DailyInvestmentReportComposer,
    ReportBodyFormat,
    ReportMode,
)


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
        email_service: EmailService | None = None,
    ) -> None:
        self._composer = composer or DailyInvestmentReportComposer()
        self._email_service = email_service

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
            if self._email_service is None:
                raise ValueError("email service is required when email_recipient is set")
            self._email_service.send(
                body,
                recipient=request.email_recipient,
                as_of_date=request.as_of_date,
                mode=request.mode,
                content_type=ReportBodyFormat.INTERACTIVE_HTML_EMAIL.content_type,
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
    body_format: ReportBodyFormat | str = ReportBodyFormat.INTERACTIVE_HTML_EMAIL,
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
