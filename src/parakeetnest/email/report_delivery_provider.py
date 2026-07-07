"""Report delivery adapter for provider-neutral email providers."""

from __future__ import annotations

from dataclasses import dataclass

from parakeetnest.email.provider import EmailProvider
from parakeetnest.research.delivery import (
    ReportDeliveryRequest,
    ReportDeliveryResult,
)


@dataclass
class EmailReportDeliveryProvider:
    """Deliver reports through an EmailProvider without exposing email details."""

    email_provider: EmailProvider
    provider_name: str = "email"

    def deliver(self, request: ReportDeliveryRequest) -> ReportDeliveryResult:
        """Deliver a report request as an email."""
        try:
            self.email_provider.send(
                subject=request.subject,
                body=request.body,
                recipient=request.recipient.email,
                content_type=request.content_type,
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures.
            return ReportDeliveryResult.failed(
                provider_name=self.provider_name,
                error_message=str(exc) or exc.__class__.__name__,
            )
        return ReportDeliveryResult.delivered(
            provider_name=self.provider_name,
            message_id=getattr(self.email_provider, "last_message_id", None),
        )


__all__ = ["EmailReportDeliveryProvider"]
