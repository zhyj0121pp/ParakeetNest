"""Email provider interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailProvider(Protocol):
    """Contract implemented by email delivery adapters."""

    def send(
        self,
        subject: str,
        body: str,
        recipient: str,
        *,
        content_type: str = "text/plain",
        attachments: tuple[object, ...] | None = None,
    ) -> None:
        """Send an email message."""
        ...
