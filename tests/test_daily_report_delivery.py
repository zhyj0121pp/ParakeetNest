"""Tests for daily investment report delivery orchestration."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Mapping

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
        body_format: ReportBodyFormat | str = ReportBodyFormat.INTERACTIVE_HTML_EMAIL,
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
    ) -> ReportDeliveryResult:
        self.calls.append(
            {
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "content_type": content_type,
                "metadata": metadata,
            }
        )
        return ReportDeliveryResult.delivered(
            provider_name="fake",
            message_id="fake-123",
        )


def test_daily_delivery_composes_and_delivers_interactive_html_by_default() -> None:
    provider = NoOpReportDeliveryProvider(message_id="noop-daily-123")
    service = DailyReportDeliveryService(
        delivery_service=ReportDeliveryService(provider),
    )

    result = service.deliver(
        DailyReportDeliveryRequest(
            tickers=("NVDA",),
            recipient_email="investor@example.com",
            generated_at=GENERATED_AT,
        )
    )

    assert result.status is ReportDeliveryStatus.DELIVERED
    assert result.provider_name == "noop"
    assert result.message_id == "noop-daily-123"
    assert len(provider.requests) == 1
    assert provider.requests[0].recipient.email == "investor@example.com"
    assert provider.requests[0].subject == "Daily Investment Report - 2026-07-01"
    assert "Tickers: NVDA" in provider.requests[0].body
    assert provider.requests[0].content_type == "text/html"


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
            "body_format": ReportBodyFormat.INTERACTIVE_HTML_EMAIL,
        }
    ]


def test_daily_delivery_passes_delivery_inputs_to_delivery_service() -> None:
    composer = FakeComposer(body="rendered daily body")
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=composer,
        delivery_service=delivery_service,
    )
    metadata = {"run_id": "epic-029", "source": "daily-use-case"}

    result = service.deliver(
        DailyReportDeliveryRequest(
            tickers=("NVDA",),
            recipient_email="investor@example.com",
            subject="Custom Daily Report",
            metadata=metadata,
        )
    )

    assert result.message_id == "fake-123"
    assert delivery_service.calls == [
        {
            "recipient_email": "investor@example.com",
            "subject": "Custom Daily Report",
            "body": "rendered daily body",
            "content_type": "text/html",
            "metadata": metadata,
        }
    ]


def test_daily_delivery_can_request_interactive_html_email() -> None:
    composer = FakeComposer(body="<!doctype html>\n<html></html>\n")
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=composer,
        delivery_service=delivery_service,
    )

    service.deliver(
        DailyReportDeliveryRequest(
            tickers=("NVDA",),
            recipient_email="investor@example.com",
            body_format=ReportBodyFormat.INTERACTIVE_HTML_EMAIL,
        )
    )

    assert composer.calls[0]["body_format"] is (
        ReportBodyFormat.INTERACTIVE_HTML_EMAIL
    )
    assert delivery_service.calls[0]["body"] == "<!doctype html>\n<html></html>\n"
    assert delivery_service.calls[0]["content_type"] == "text/html"


def test_daily_delivery_builds_default_subject_from_as_of_date() -> None:
    delivery_service = FakeDeliveryService()
    service = DailyReportDeliveryService(
        composer=FakeComposer(),
        delivery_service=delivery_service,
    )

    service.deliver(
        DailyReportDeliveryRequest(
            tickers=("NVDA",),
            recipient_email="investor@example.com",
            as_of_date=AS_OF_DATE,
        )
    )

    assert delivery_service.calls[0]["subject"] == (
        "Daily Investment Report - 2026-07-01"
    )
