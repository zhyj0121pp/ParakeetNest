"""Tests for provider-neutral email delivery."""

from __future__ import annotations

from datetime import date

import pytest

from parakeetnest.email import ConsoleEmailProvider, EmailService


class RecordingEmailProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send(self, subject: str, body: str, recipient: str) -> None:
        self.calls.append(
            {
                "subject": subject,
                "body": body,
                "recipient": recipient,
            }
        )


def test_email_service_delegates_to_provider() -> None:
    provider = RecordingEmailProvider()
    service = EmailService(provider)

    message = service.send(
        "daily report body",
        recipient="investor@example.com",
        as_of_date=date(2026, 7, 1),
    )

    assert message.subject == "Daily Investment Report - 2026-07-01"
    assert message.body == "daily report body"
    assert message.recipient == "investor@example.com"
    assert provider.calls == [
        {
            "subject": "Daily Investment Report - 2026-07-01",
            "body": "daily report body",
            "recipient": "investor@example.com",
        }
    ]


def test_email_service_validates_recipient_before_delegating() -> None:
    provider = RecordingEmailProvider()

    with pytest.raises(ValueError, match="valid email"):
        EmailService(provider).send("daily report body", recipient="not-email")

    assert provider.calls == []


def test_console_email_provider_prints_message(capsys: pytest.CaptureFixture[str]) -> None:
    ConsoleEmailProvider().send(
        subject="Daily Investment Report - 2026-07-01",
        body="daily report body\n",
        recipient="investor@example.com",
    )

    assert capsys.readouterr().out == (
        "==== EMAIL ====\n"
        "To: investor@example.com\n"
        "Subject: Daily Investment Report - 2026-07-01\n"
        "\n"
        "daily report body\n"
        "\n"
        "==============\n"
    )
