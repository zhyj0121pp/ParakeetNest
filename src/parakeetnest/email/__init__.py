"""Provider-neutral email delivery support."""

from parakeetnest.email.console_provider import ConsoleEmailProvider
from parakeetnest.email.models import EmailMessage
from parakeetnest.email.provider import EmailProvider
from parakeetnest.email.service import EmailService

__all__ = [
    "ConsoleEmailProvider",
    "EmailMessage",
    "EmailProvider",
    "EmailService",
]
