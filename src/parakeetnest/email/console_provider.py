"""Console email provider for local end-to-end validation."""

from __future__ import annotations

import sys
from typing import TextIO


class ConsoleEmailProvider:
    """Print email messages instead of sending them."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream

    def send(
        self,
        subject: str,
        body: str,
        recipient: str,
        *,
        content_type: str = "text/plain",
        attachments: tuple[object, ...] | None = None,
    ) -> None:
        """Print an email envelope and body."""
        stream = self._stream or sys.stdout
        print("==== EMAIL ====", file=stream)
        print(f"To: {recipient}", file=stream)
        print(f"Subject: {subject}", file=stream)
        print("", file=stream)
        print(body, end="" if body.endswith("\n") else "\n", file=stream)
        for attachment in attachments or ():
            print(
                f"Attachment: {attachment.filename} ({attachment.content_type})",
                file=stream,
            )
        print("", file=stream)
        print("==============", file=stream)
