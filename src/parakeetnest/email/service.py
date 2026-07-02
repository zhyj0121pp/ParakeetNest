"""Provider-neutral email service for daily reports."""

from __future__ import annotations

from datetime import date

from parakeetnest.email.models import EmailMessage
from parakeetnest.email.provider import EmailProvider


class EmailService:
    """Build daily report email messages and delegate delivery."""

    def __init__(self, provider: EmailProvider) -> None:
        self._provider = provider

    def send(
        self,
        report: str,
        *,
        recipient: str,
        as_of_date: date | None = None,
    ) -> EmailMessage:
        """Send a generated daily report through the configured provider."""
        message = EmailMessage(
            subject=self._build_subject(as_of_date=as_of_date),
            body=report,
            recipient=recipient,
        )
        self._provider.send(
            subject=message.subject,
            body=message.body,
            recipient=message.recipient,
        )
        return message

    def _build_subject(self, *, as_of_date: date | None = None) -> str:
        report_date = as_of_date or date.today()
        return f"Daily Investment Report - {report_date.isoformat()}"
