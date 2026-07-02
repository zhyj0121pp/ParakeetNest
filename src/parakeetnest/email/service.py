"""Provider-neutral email service for daily reports."""

from __future__ import annotations

from datetime import date

from parakeetnest.email.models import EmailMessage
from parakeetnest.email.provider import EmailProvider
from parakeetnest.research.models import ReportMode


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
        mode: ReportMode | str | None = None,
    ) -> EmailMessage:
        """Send a generated daily report through the configured provider."""
        message = EmailMessage(
            subject=self._build_subject(as_of_date=as_of_date, mode=mode),
            body=report,
            recipient=recipient,
        )
        self._provider.send(
            subject=message.subject,
            body=message.body,
            recipient=message.recipient,
        )
        return message

    def _build_subject(
        self,
        *,
        as_of_date: date | None = None,
        mode: ReportMode | str | None = None,
    ) -> str:
        report_date = as_of_date or date.today()
        if mode is None:
            title = "Daily Investment Report"
        else:
            title = ReportMode.from_value(mode).title
        return f"{title} - {report_date.isoformat()}"
