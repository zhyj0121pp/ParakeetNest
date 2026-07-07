"""Email delivery models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    """Provider-neutral email message."""

    subject: str
    body: str
    recipient: str
    content_type: str = "text/plain"

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _required_text(self.subject, "subject"))
        object.__setattr__(self, "body", _required_text(self.body, "body"))
        object.__setattr__(self, "recipient", _required_email(self.recipient))
        object.__setattr__(
            self,
            "content_type",
            _normalize_content_type(self.content_type),
        )


def _required_email(value: str) -> str:
    email = _required_text(value, "recipient")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("recipient must be a valid email address")
    return email


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_content_type(value: str) -> str:
    content_type = _required_text(value, "content_type").lower()
    if content_type not in {"text/plain", "text/html"}:
        raise ValueError("content_type must be text/plain or text/html")
    return content_type
