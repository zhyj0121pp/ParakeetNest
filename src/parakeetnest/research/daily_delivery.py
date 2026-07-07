"""Daily investment report composition and delivery use case."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Protocol

from parakeetnest.research.composer import (
    DailyInvestmentReportComposer,
    ReportBodyFormat,
)
from parakeetnest.research.delivery import (
    ReportDeliveryAttachment,
    ReportDeliveryResult,
)
from parakeetnest.research.localization import ReportLanguage, get_report_localization


class _DailyReportComposer(Protocol):
    def compose(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        body_format: ReportBodyFormat | str = ReportBodyFormat.INTERACTIVE_HTML_EMAIL,
    ) -> str:
        """Compose a daily investment report body."""


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


@dataclass(frozen=True)
class DailyReportDeliveryRequest:
    """Request to compose and deliver a daily investment report."""

    tickers: tuple[str, ...] | list[str]
    recipient_email: str
    account_id: str | None = None
    as_of_date: date | None = None
    generated_at: datetime | None = None
    subject: str | None = None
    body_format: ReportBodyFormat | str = ReportBodyFormat.INTERACTIVE_HTML_EMAIL
    metadata: Mapping[str, str] | None = field(default_factory=dict)


class DailyReportDeliveryService:
    """Use case for composing and delivering the daily investment report."""

    def __init__(
        self,
        *,
        delivery_service: _ReportDeliveryService,
        composer: _DailyReportComposer | None = None,
    ) -> None:
        self._composer = composer or DailyInvestmentReportComposer()
        self._delivery_service = delivery_service

    def deliver(self, request: DailyReportDeliveryRequest) -> ReportDeliveryResult:
        """Compose the daily report body and deliver it through the delivery service."""
        body_format = ReportBodyFormat.from_value(request.body_format)
        body = self._composer.compose(
            request.tickers,
            account_id=request.account_id,
            as_of_date=request.as_of_date,
            generated_at=request.generated_at,
            body_format=body_format,
        )
        report_date = _report_date(
            as_of_date=request.as_of_date,
            generated_at=request.generated_at,
        )
        subject = request.subject or _default_subject(
            as_of_date=request.as_of_date,
            generated_at=request.generated_at,
        )
        attachments: tuple[ReportDeliveryAttachment, ...] = ()
        if _is_html_attachment_format(body_format):
            localization = get_report_localization()
            filename = f"morning-report-{report_date.isoformat()}.html"
            attachment_content = body
            body = _minimal_attachment_body(
                title=localization.report_title,
                report_date=report_date,
                attachment_filename=filename,
                language=localization.language,
            )
            subject = (
                request.subject
                or f"{localization.report_title} - {report_date.isoformat()}"
            )
            attachments = (
                ReportDeliveryAttachment(
                    filename=filename,
                    content=attachment_content,
                    content_type="text/html",
                ),
            )
        return self._delivery_service.deliver_report(
            recipient_email=request.recipient_email,
            subject=subject,
            body=body,
            content_type=body_format.content_type,
            metadata=request.metadata if request.metadata is not None else {},
            attachments=attachments,
        )


def _default_subject(
    *,
    as_of_date: date | None = None,
    generated_at: datetime | None = None,
) -> str:
    report_date = _report_date(as_of_date=as_of_date, generated_at=generated_at)
    return f"Daily Investment Report - {report_date.isoformat()}"


def _report_date(
    *,
    as_of_date: date | None = None,
    generated_at: datetime | None = None,
) -> date:
    report_date = as_of_date
    if report_date is None and generated_at is not None:
        report_date = generated_at.date()
    if report_date is None:
        report_date = date.today()
    return report_date


def _is_html_attachment_format(body_format: ReportBodyFormat) -> bool:
    return body_format in {
        ReportBodyFormat.HTML_ATTACHMENT_ONLY,
        ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
    }


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


__all__ = [
    "DailyReportDeliveryRequest",
    "DailyReportDeliveryService",
]
