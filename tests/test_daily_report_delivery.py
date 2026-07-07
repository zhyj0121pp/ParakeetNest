"""Tests for daily investment report delivery orchestration."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Mapping

from parakeetnest.config import get_settings
from parakeetnest.research import (
    DailyReportDeliveryRequest,
    DailyReportDeliveryService,
    NoOpReportDeliveryProvider,
    ReportBodyFormat,
    ReportDeliveryResult,
    ReportDeliveryService,
    ReportDeliveryStatus,
)


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)
AS_OF_DATE = date(2026, 7, 1)


class FakeComposer:
    def __init__(self, body: str = "daily report body") -> None:
        self.body = body
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        body_format: ReportBodyFormat | str = (
            ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT
        ),
    ) -> str:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "generated_at": generated_at,
                "body_format": body_format,
            }
        )
        return self.body


class FakeDeliveryService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def deliver_report(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        content_type: str = "text/plain",
        metadata: Mapping[str, str] | None = None,
        attachments: tuple[object, ...] | None = None,
    ) -> ReportDeliveryResult:
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
        return ReportDeliveryResult.delivered(
            provider_name="fake",
            message_id="fake-123",
        )


def test_daily_delivery_sends_interactive_html_attachment_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    provider = NoOpReportDeliveryProvider(message_id="noop-daily-123")
    service = DailyReportDeliveryService(
        delivery_service=ReportDeliveryService(provider),
    )

    try:
        result = service.deliver(
            DailyReportDeliveryRequest(
                tickers=("NVDA",),
                recipient_email="investor@example.com",
                generated_at=GENERATED_AT,
            )
        )
    finally:
        get_settings.cache_clear()

    assert result.status is ReportDeliveryStatus.DELIVERED
    assert result.provider_name == "noop"
    assert result.message_id == "noop-daily-123"
    assert len(provider.requests) == 1
    assert provider.requests[0].recipient.email == "investor@example.com"
    request = provider.requests[0]
    assert request.subject == "Morning Investment Report - 2026-07-01"
    assert request.body == (
        "Morning Investment Report\n"
        "Date: 2026-07-01\n"
        "Full report is attached: morning-report-2026-07-01.html"
    )
    assert "Tickers: NVDA" not in request.body
    assert "Recommendation" not in request.body
    assert request.content_type == "text/plain"
    assert len(request.attachments) == 1
    attachment = request.attachments[0]
    assert attachment.filename == "morning-report-2026-07-01.html"
    assert attachment.filename.endswith(".html")
    assert attachment.content_type == "text/html"
    assert attachment.content.startswith("<!doctype html>")
    assert "<details" in attachment.content
    assert "<summary" in attachment.content


def test_daily_delivery_passes_research_inputs_to_composer() -> None:
    composer = FakeComposer()
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=composer,
        delivery_service=delivery_service,
    )

    service.deliver(
        DailyReportDeliveryRequest(
            tickers=["NVDA", "AAPL"],
            recipient_email="investor@example.com",
            account_id="main",
            as_of_date=AS_OF_DATE,
            generated_at=GENERATED_AT,
        )
    )

    assert composer.calls == [
        {
            "tickers": ["NVDA", "AAPL"],
            "account_id": "main",
            "as_of_date": AS_OF_DATE,
            "generated_at": GENERATED_AT,
            "body_format": ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
        }
    ]


def test_daily_delivery_passes_delivery_inputs_to_delivery_service(monkeypatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    composer = FakeComposer(body="rendered daily body")
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=composer,
        delivery_service=delivery_service,
    )
    metadata = {"run_id": "epic-029", "source": "daily-use-case"}

    try:
        result = service.deliver(
            DailyReportDeliveryRequest(
                tickers=("NVDA",),
                recipient_email="investor@example.com",
                subject="Custom Daily Report",
                as_of_date=AS_OF_DATE,
                metadata=metadata,
            )
        )
    finally:
        get_settings.cache_clear()

    assert result.message_id == "fake-123"
    assert len(delivery_service.calls) == 1
    call = delivery_service.calls[0]
    assert call["recipient_email"] == "investor@example.com"
    assert call["subject"] == "Custom Daily Report"
    assert call["body"] == (
        "Morning Investment Report\n"
        "Date: 2026-07-01\n"
        "Full report is attached: morning-report-2026-07-01.html\n"
    )
    assert call["content_type"] == "text/plain"
    assert call["metadata"] == metadata
    attachment = call["attachments"][0]
    assert attachment.filename == "morning-report-2026-07-01.html"
    assert attachment.content == "rendered daily body"
    assert attachment.content_type == "text/html"


def test_daily_delivery_can_send_interactive_html_as_attachment_only(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    composer = FakeComposer(
        body=(
            "<!doctype html>\n"
            "<html><body><details><summary>NVDA</summary>"
            "Recommendation: Trim $100 10 shares"
            "</details></body></html>\n"
        )
    )
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=composer,
        delivery_service=delivery_service,
    )

    try:
        service.deliver(
            DailyReportDeliveryRequest(
                tickers=("NVDA",),
                recipient_email="investor@example.com",
                as_of_date=AS_OF_DATE,
            )
        )
    finally:
        get_settings.cache_clear()

    call = delivery_service.calls[0]
    assert call["subject"] == "Morning Investment Report - 2026-07-01"
    assert call["body"] == (
        "Morning Investment Report\n"
        "Date: 2026-07-01\n"
        "Full report is attached: morning-report-2026-07-01.html\n"
    )
    assert "Recommendation" not in call["body"]
    assert "NVDA" not in call["body"]
    assert "$100" not in call["body"]
    assert "10 shares" not in call["body"]
    assert call["content_type"] == "text/plain"
    attachment = call["attachments"][0]
    assert attachment.filename == "morning-report-2026-07-01.html"
    assert attachment.filename.endswith(".html")
    assert attachment.content_type == "text/html"
    assert attachment.content.startswith("<!doctype html>")
    assert "<details>" in attachment.content
    assert "<summary>" in attachment.content


def test_daily_delivery_attachment_only_localizes_chinese_body(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "zh")
    get_settings.cache_clear()
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=FakeComposer(
            body="<!doctype html>\n<details><summary>详情</summary></details>\n"
        ),
        delivery_service=delivery_service,
    )

    try:
        service.deliver(
            DailyReportDeliveryRequest(
                tickers=("NVDA",),
                recipient_email="investor@example.com",
                as_of_date=AS_OF_DATE,
            )
        )
    finally:
        get_settings.cache_clear()

    call = delivery_service.calls[0]
    assert call["subject"] == "早间投资报告 - 2026-07-01"
    assert call["body"] == (
        "早间投资报告\n"
        "日期：2026-07-01\n"
        "完整报告请查看附件：morning-report-2026-07-01.html\n"
    )


def test_daily_delivery_builds_default_attachment_subject_from_as_of_date(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=FakeComposer(),
        delivery_service=delivery_service,
    )

    try:
        service.deliver(
            DailyReportDeliveryRequest(
                tickers=("NVDA",),
                recipient_email="investor@example.com",
                as_of_date=AS_OF_DATE,
            )
        )
    finally:
        get_settings.cache_clear()

    assert delivery_service.calls[0]["subject"] == (
        "Morning Investment Report - 2026-07-01"
    )
