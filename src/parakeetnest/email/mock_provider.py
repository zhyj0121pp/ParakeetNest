"""Mock email provider for tests and default local wiring."""

from __future__ import annotations

from parakeetnest.email.models import EmailMessage


class MockEmailProvider:
    """Record email messages without sending them."""

    provider_name = "mock"

    def __init__(self) -> None:
        self._messages: list[EmailMessage] = []

    @property
    def messages(self) -> tuple[EmailMessage, ...]:
        """Return messages accepted by this provider."""
        return tuple(self._messages)

    def send(
        self,
        subject: str,
        body: str,
        recipient: str,
        *,
        content_type: str = "text/plain",
        attachments: tuple[object, ...] | None = None,
    ) -> None:
        """Record a provider-neutral email message."""
        self._messages.append(
            EmailMessage(
                subject=subject,
                body=body,
                recipient=recipient,
                content_type=content_type,
                attachments=attachments or (),
            )
        )


__all__ = ["MockEmailProvider"]
