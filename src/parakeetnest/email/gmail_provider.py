"""Gmail email provider behind the provider-neutral email interface."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from email.message import EmailMessage as MimeEmailMessage
import os
from pathlib import Path
from typing import Any

from parakeetnest.email.models import EmailAttachment, EmailMessage
from parakeetnest.exceptions import ConfigurationError


GMAIL_SEND_SCOPES = ("https://www.googleapis.com/auth/gmail.send",)


class GmailDeliveryError(RuntimeError):
    """Raised when Gmail rejects or fails a send request."""


@dataclass
class GmailEmailProvider:
    """Send provider-neutral email messages through Gmail."""

    credentials_path_env_var: str = "GOOGLE_APPLICATION_CREDENTIALS"
    token_path_env_var: str = "PARAKEETNEST_GMAIL_TOKEN_PATH"
    sender_email: str | None = None
    client: Any | None = None
    user_id: str = "me"

    provider_name = "gmail"

    def __post_init__(self) -> None:
        self.last_message_id: str | None = None
        if self.client is not None:
            return
        self.client = self._build_client()

    def send(
        self,
        subject: str,
        body: str,
        recipient: str,
        *,
        content_type: str = "text/plain",
        attachments: tuple[EmailAttachment, ...] | None = None,
    ) -> None:
        """Send an email message through Gmail."""
        message = EmailMessage(
            subject=subject,
            body=body,
            recipient=recipient,
            content_type=content_type,
            attachments=attachments or (),
        )
        raw_message = self._encode_message(message)
        try:
            response = (
                self.client.users()
                .messages()
                .send(userId=self.user_id, body={"raw": raw_message})
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures.
            raise GmailDeliveryError(str(exc) or exc.__class__.__name__) from exc
        self.last_message_id = _read(response, "id")

    def _build_client(self) -> Any:
        credentials_path = _configured_existing_path(
            self.credentials_path_env_var,
            "Gmail provider requires credentials from the configured environment variable.",
        )
        token_path = _configured_existing_path(
            self.token_path_env_var,
            "Gmail provider requires an OAuth token from the configured environment variable.",
        )
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as error:
            raise ConfigurationError(
                "Gmail email provider requires the optional 'gmail' dependencies."
            ) from error

        # credentials_path is validated so local configuration is explicit. The
        # authorized-user token is what Gmail uses for this send-only provider.
        credentials_path.resolve()
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            scopes=list(GMAIL_SEND_SCOPES),
        )
        return build("gmail", "v1", credentials=credentials)

    def _encode_message(self, message: EmailMessage) -> str:
        mime_message = MimeEmailMessage()
        if self.sender_email:
            mime_message["From"] = self.sender_email.strip()
        mime_message["To"] = message.recipient
        mime_message["Subject"] = message.subject
        if message.content_type == "text/html":
            mime_message.set_content("")
            mime_message.add_alternative(message.body, subtype="html")
        else:
            mime_message.set_content(message.body)
        for attachment in message.attachments:
            _, subtype = attachment.content_type.split("/", 1)
            mime_message.add_attachment(
                attachment.content,
                subtype=subtype,
                filename=attachment.filename,
            )
        raw_bytes = mime_message.as_bytes()
        return base64.urlsafe_b64encode(raw_bytes).decode("ascii")


def _configured_existing_path(env_var_name: str, error_message: str) -> Path:
    normalized_env_var = str(env_var_name).strip()
    if not normalized_env_var:
        raise ConfigurationError(error_message)
    configured_path = os.environ.get(normalized_env_var)
    if configured_path is None or not configured_path.strip():
        raise ConfigurationError(error_message)
    path = Path(configured_path).expanduser()
    if not path.exists():
        raise ConfigurationError(f"{error_message} Missing path: {path}")
    return path


def _read(value: Any, key: str) -> str | None:
    if isinstance(value, dict):
        result = value.get(key)
    else:
        result = getattr(value, key, None)
    if result is None:
        return None
    normalized = str(result).strip()
    return normalized or None


__all__ = ["GMAIL_SEND_SCOPES", "GmailDeliveryError", "GmailEmailProvider"]
