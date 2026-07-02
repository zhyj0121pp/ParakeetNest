"""Email delivery models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    """Provider-neutral plain-text email message."""

    subject: str
    body: str
    recipient: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _required_text(self.subject, "subject"))
        object.__setattr__(self, "body", _required_text(self.body, "body"))
        object.__setattr__(self, "recipient", _required_email(self.recipient))


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
