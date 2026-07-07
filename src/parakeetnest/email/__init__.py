"""Provider-neutral email delivery support."""

from parakeetnest.email.console_provider import ConsoleEmailProvider
from parakeetnest.email.gmail_provider import GmailDeliveryError, GmailEmailProvider
from parakeetnest.email.mock_provider import MockEmailProvider
from parakeetnest.email.models import EmailAttachment, EmailMessage
from parakeetnest.email.provider import EmailProvider
from parakeetnest.email.registry import (
    EmailProviderRegistry,
    create_email_provider_registry,
)
from parakeetnest.email.report_delivery_provider import EmailReportDeliveryProvider
from parakeetnest.email.service import EmailService

__all__ = [
    "ConsoleEmailProvider",
    "EmailProviderRegistry",
    "EmailMessage",
    "EmailAttachment",
    "EmailProvider",
    "EmailReportDeliveryProvider",
    "EmailService",
    "GmailDeliveryError",
    "GmailEmailProvider",
    "MockEmailProvider",
    "create_email_provider_registry",
]
