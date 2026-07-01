"""Tests for provider-neutral report delivery."""

from __future__ import annotations

import pytest

from parakeetnest.research import (
    NoOpReportDeliveryProvider,
    ReportDeliveryRequest,
    ReportDeliveryResult,
    ReportDeliveryService,
    ReportDeliveryStatus,
    ReportRecipient,
)


class ExplodingDeliveryProvider:
    provider_name = "exploding"

    def deliver(self, request: ReportDeliveryRequest) -> ReportDeliveryResult:
        raise RuntimeError("provider unavailable")


def test_can_create_delivery_request_with_normalized_fields() -> None:
    request = ReportDeliveryRequest(
        recipient=ReportRecipient(email=" investor@example.com "),
        subject=" Daily report ",
        body=" Plain-text report body. ",
        metadata={" run_id ": " epic-028 ", " ": "ignored"},
    )

    assert request.recipient.email == "investor@example.com"
    assert request.subject == "Daily report"
    assert request.body == "Plain-text report body."
    assert request.metadata == {"run_id": "epic-028"}


def test_delivery_request_validates_required_inputs() -> None:
    with pytest.raises(ValueError, match="valid email"):
        ReportRecipient(email="not-an-email")

    with pytest.raises(ValueError, match="subject is required"):
        ReportDeliveryRequest(
            recipient=ReportRecipient(email="investor@example.com"),
            subject=" ",
            body="Report body.",
        )

    with pytest.raises(ValueError, match="body is required"):
        ReportDeliveryRequest(
            recipient=ReportRecipient(email="investor@example.com"),
            subject="Daily report",
            body=" ",
        )


def test_can_deliver_via_noop_provider() -> None:
    provider = NoOpReportDeliveryProvider(message_id="noop-123")
    service = ReportDeliveryService(provider)

    result = service.deliver_report(
        recipient_email="investor@example.com",
        subject="Daily report",
        body="Plain-text report body.",
        metadata={"report_date": "2026-07-01"},
    )

    assert result.status is ReportDeliveryStatus.DELIVERED
    assert result.provider_name == "noop"
    assert result.message_id == "noop-123"
    assert result.error_message is None
    assert len(provider.requests) == 1
    assert provider.requests[0].recipient.email == "investor@example.com"


def test_noop_provider_can_return_failed_result() -> None:
    provider = NoOpReportDeliveryProvider(fail_with="simulated delivery failure")
    service = ReportDeliveryService(provider)

    result = service.deliver_report(
        recipient_email="investor@example.com",
        subject="Daily report",
        body="Plain-text report body.",
    )

    assert result.status is ReportDeliveryStatus.FAILED
    assert result.provider_name == "noop"
    assert result.message_id is None
    assert result.error_message == "simulated delivery failure"


def test_service_captures_provider_exceptions_as_failed_results() -> None:
    service = ReportDeliveryService(ExplodingDeliveryProvider())
    request = ReportDeliveryRequest(
        recipient=ReportRecipient(email="investor@example.com"),
        subject="Daily report",
        body="Plain-text report body.",
    )

    result = service.deliver(request)

    assert result.status is ReportDeliveryStatus.FAILED
    assert result.provider_name == "exploding"
    assert result.error_message == "provider unavailable"


def test_failed_result_requires_error_message() -> None:
    with pytest.raises(ValueError, match="error_message is required"):
        ReportDeliveryResult(
            status=ReportDeliveryStatus.FAILED,
            provider_name="noop",
        )
