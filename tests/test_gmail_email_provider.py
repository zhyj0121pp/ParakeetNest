"""Tests for the optional Gmail email provider."""

from __future__ import annotations

import base64
from email import message_from_bytes
from pathlib import Path

import pytest

from parakeetnest.config import EmailConfig
from parakeetnest.email import (
    EmailAttachment,
    EmailReportDeliveryProvider,
    GmailDeliveryError,
    GmailEmailProvider,
    MockEmailProvider,
    create_email_provider_registry,
)
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.research import (
    ReportDeliveryAttachment,
    ReportDeliveryRequest,
    ReportDeliveryStatus,
    ReportRecipient,
)


class FakeGmailSendRequest:
    def __init__(self, response: dict[str, str] | None, error: Exception | None) -> None:
        self._response = response or {}
        self._error = error

    def execute(self) -> dict[str, str]:
        if self._error is not None:
            raise self._error
        return self._response


class FakeGmailMessages:
    def __init__(self, client: FakeGmailClient) -> None:
        self._client = client

    def send(self, *, userId: str, body: dict[str, str]) -> FakeGmailSendRequest:
        self._client.send_calls.append({"userId": userId, "body": body})
        return FakeGmailSendRequest(self._client.response, self._client.error)


class FakeGmailUsers:
    def __init__(self, client: FakeGmailClient) -> None:
        self._client = client

    def messages(self) -> FakeGmailMessages:
        return FakeGmailMessages(self._client)


class FakeGmailClient:
    def __init__(
        self,
        *,
        response: dict[str, str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or {"id": "gmail-123"}
        self.error = error
        self.send_calls: list[dict[str, object]] = []

    def users(self) -> FakeGmailUsers:
        return FakeGmailUsers(self)


def test_gmail_provider_sends_plain_text_email_with_fake_client() -> None:
    client = FakeGmailClient(response={"id": "gmail-message-123"})
    provider = GmailEmailProvider(
        client=client,
        sender_email="sender@example.com",
    )

    provider.send(
        subject="Daily Investment Report - 2026-07-01",
        body="Plain-text report body.",
        recipient="investor@example.com",
    )

    assert provider.last_message_id == "gmail-message-123"
    assert len(client.send_calls) == 1
    assert client.send_calls[0]["userId"] == "me"
    encoded = client.send_calls[0]["body"]["raw"]
    decoded = message_from_bytes(base64.urlsafe_b64decode(encoded.encode("ascii")))
    assert decoded["From"] == "sender@example.com"
    assert decoded["To"] == "investor@example.com"
    assert decoded["Subject"] == "Daily Investment Report - 2026-07-01"
    assert decoded.get_payload() == "Plain-text report body.\n"


def test_gmail_provider_sends_html_email_as_mime_alternative() -> None:
    client = FakeGmailClient(response={"id": "gmail-html-123"})
    provider = GmailEmailProvider(
        client=client,
        sender_email="sender@example.com",
    )

    provider.send(
        subject="Daily Investment Report - 2026-07-01",
        body="<!doctype html>\n<html><body>HTML report body.</body></html>\n",
        recipient="investor@example.com",
        content_type="text/html",
    )

    assert provider.last_message_id == "gmail-html-123"
    encoded = client.send_calls[0]["body"]["raw"]
    decoded = message_from_bytes(base64.urlsafe_b64decode(encoded.encode("ascii")))
    html_parts = [
        part
        for part in decoded.walk()
        if part.get_content_type() == "text/html"
    ]
    assert decoded.is_multipart()
    assert len(html_parts) == 1
    assert html_parts[0].get_payload(decode=True).decode("utf-8").startswith(
        "<!doctype html>\n"
    )


def test_gmail_provider_sends_html_attachment() -> None:
    client = FakeGmailClient(response={"id": "gmail-attachment-123"})
    provider = GmailEmailProvider(
        client=client,
        sender_email="sender@example.com",
    )

    provider.send(
        subject="Morning Investment Report - 2026-07-01",
        body=(
            "Morning Investment Report\n"
            "Date: 2026-07-01\n"
            "Full report is attached: morning-report-2026-07-01.html\n"
        ),
        recipient="investor@example.com",
        attachments=(
            EmailAttachment(
                filename="morning-report-2026-07-01.html",
                content=(
                    "<!doctype html>\n"
                    "<html><body><details><summary>NVDA</summary>"
                    "Recommendation: Trim</details></body></html>\n"
                ),
                content_type="text/html",
            ),
        ),
    )

    assert provider.last_message_id == "gmail-attachment-123"
    encoded = client.send_calls[0]["body"]["raw"]
    decoded = message_from_bytes(base64.urlsafe_b64decode(encoded.encode("ascii")))
    attachment_parts = [
        part
        for part in decoded.walk()
        if part.get_filename() == "morning-report-2026-07-01.html"
    ]
    assert len(attachment_parts) == 1
    assert attachment_parts[0].get_content_type() == "text/html"
    assert attachment_parts[0].get_payload(decode=True).decode("utf-8").startswith(
        "<!doctype html>\n"
    )


def test_gmail_provider_validates_message_before_calling_client() -> None:
    client = FakeGmailClient()
    provider = GmailEmailProvider(client=client)

    with pytest.raises(ValueError, match="valid email"):
        provider.send(
            subject="Daily Investment Report",
            body="Plain-text report body.",
            recipient="not-an-email",
        )

    assert client.send_calls == []


def test_gmail_provider_wraps_api_errors() -> None:
    provider = GmailEmailProvider(
        client=FakeGmailClient(error=RuntimeError("gmail unavailable"))
    )

    with pytest.raises(GmailDeliveryError, match="gmail unavailable"):
        provider.send(
            subject="Daily Investment Report",
            body="Plain-text report body.",
            recipient="investor@example.com",
        )


def test_gmail_provider_requires_configured_credentials_and_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_GMAIL_CREDENTIALS", raising=False)
    monkeypatch.delenv("TEST_GMAIL_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="credentials"):
        GmailEmailProvider(
            credentials_path_env_var="TEST_GMAIL_CREDENTIALS",
            token_path_env_var="TEST_GMAIL_TOKEN",
        )


def test_gmail_provider_reports_missing_token_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("TEST_GMAIL_CREDENTIALS", str(credentials_path))
    monkeypatch.setenv("TEST_GMAIL_TOKEN", str(tmp_path / "missing-token.json"))

    with pytest.raises(ConfigurationError, match="OAuth token"):
        GmailEmailProvider(
            credentials_path_env_var="TEST_GMAIL_CREDENTIALS",
            token_path_env_var="TEST_GMAIL_TOKEN",
        )


def test_email_report_delivery_provider_returns_gmail_message_id() -> None:
    gmail_provider = GmailEmailProvider(
        client=FakeGmailClient(response={"id": "gmail-report-123"})
    )
    delivery_provider = EmailReportDeliveryProvider(
        gmail_provider,
        provider_name="gmail",
    )

    result = delivery_provider.deliver(
        ReportDeliveryRequest(
            recipient=ReportRecipient(email="investor@example.com"),
            subject="Daily Investment Report",
            body="Plain-text report body.",
        )
    )

    assert result.status is ReportDeliveryStatus.DELIVERED
    assert result.provider_name == "gmail"
    assert result.message_id == "gmail-report-123"


def test_email_report_delivery_provider_passes_html_attachments() -> None:
    email_provider = MockEmailProvider()
    delivery_provider = EmailReportDeliveryProvider(
        email_provider,
        provider_name="mock",
    )

    result = delivery_provider.deliver(
        ReportDeliveryRequest(
            recipient=ReportRecipient(email="investor@example.com"),
            subject="Morning Investment Report",
            body="Full report is attached: morning-report-2026-07-01.html",
            attachments=(
                ReportDeliveryAttachment(
                    filename="morning-report-2026-07-01.html",
                    content="<!doctype html>\n<details><summary>NVDA</summary></details>\n",
                    content_type="text/html",
                ),
            ),
        )
    )

    assert result.status is ReportDeliveryStatus.DELIVERED
    assert email_provider.messages[0].attachments[0].filename.endswith(".html")
    assert email_provider.messages[0].attachments[0].content_type == "text/html"


def test_email_report_delivery_provider_returns_failed_result_on_gmail_error() -> None:
    gmail_provider = GmailEmailProvider(
        client=FakeGmailClient(error=RuntimeError("quota exceeded"))
    )
    delivery_provider = EmailReportDeliveryProvider(
        gmail_provider,
        provider_name="gmail",
    )

    result = delivery_provider.deliver(
        ReportDeliveryRequest(
            recipient=ReportRecipient(email="investor@example.com"),
            subject="Daily Investment Report",
            body="Plain-text report body.",
        )
    )

    assert result.status is ReportDeliveryStatus.FAILED
    assert result.provider_name == "gmail"
    assert result.error_message == "quota exceeded"


def test_email_provider_registry_defaults_to_mock_provider() -> None:
    registry = create_email_provider_registry()

    assert [item.provider_id for item in registry.list_registrations()] == [
        "mock",
        "gmail",
    ]
    assert isinstance(registry.resolve(EmailConfig()), MockEmailProvider)


def test_email_provider_registry_rejects_unknown_provider() -> None:
    registry = create_email_provider_registry()

    with pytest.raises(ConfigurationError, match="Unknown email provider"):
        registry.resolve("smtp")
