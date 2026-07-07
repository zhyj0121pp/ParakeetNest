"""Provider-neutral report delivery models and service."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol, runtime_checkable


class ReportDeliveryStatus(StrEnum):
    """Provider-neutral outcome of a report delivery attempt."""

    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass(frozen=True)
class ReportRecipient:
    """Recipient for a daily investment report."""

    email: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "email", _required_email(self.email))


@dataclass(frozen=True)
class ReportDeliveryRequest:
    """Provider-neutral request to deliver a report."""

    recipient: ReportRecipient
    subject: str
    body: str
    content_type: str = "text/plain"
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _required_text(self.subject, "subject"))
        object.__setattr__(self, "body", _required_text(self.body, "body"))
        object.__setattr__(
            self,
            "content_type",
            _normalize_content_type(self.content_type),
        )
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))


@dataclass(frozen=True)
class ReportDeliveryResult:
    """Provider-neutral result of a report delivery attempt."""

    status: ReportDeliveryStatus
    provider_name: str
    message_id: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ReportDeliveryStatus):
            object.__setattr__(self, "status", ReportDeliveryStatus(self.status))
        object.__setattr__(
            self,
            "provider_name",
            _required_text(self.provider_name, "provider_name"),
        )
        object.__setattr__(self, "message_id", _optional_text(self.message_id))
        object.__setattr__(self, "error_message", _optional_text(self.error_message))
        if self.status is ReportDeliveryStatus.FAILED and not self.error_message:
            raise ValueError("error_message is required for failed delivery")

    @classmethod
    def delivered(
        cls,
        *,
        provider_name: str,
        message_id: str | None = None,
    ) -> ReportDeliveryResult:
        """Create a successful delivery result."""
        return cls(
            status=ReportDeliveryStatus.DELIVERED,
            provider_name=provider_name,
            message_id=message_id,
        )

    @classmethod
    def failed(
        cls,
        *,
        provider_name: str,
        error_message: str,
        message_id: str | None = None,
    ) -> ReportDeliveryResult:
        """Create a failed delivery result."""
        return cls(
            status=ReportDeliveryStatus.FAILED,
            provider_name=provider_name,
            message_id=message_id,
            error_message=error_message,
        )


@runtime_checkable
class ReportDeliveryProvider(Protocol):
    """Contract implemented by future report delivery adapters."""

    @property
    def provider_name(self) -> str:
        """Return the provider-neutral name for this adapter."""
        ...

    def deliver(self, request: ReportDeliveryRequest) -> ReportDeliveryResult:
        """Deliver a plain-text report request."""
        ...


class NoOpReportDeliveryProvider:
    """Deterministic no-op provider for tests and local wiring."""

    provider_name = "noop"

    def __init__(
        self,
        *,
        message_id: str | None = "noop-report-delivery",
        fail_with: str | None = None,
    ) -> None:
        self._message_id = message_id
        self._fail_with = _optional_text(fail_with)
        self._requests: list[ReportDeliveryRequest] = []

    @property
    def requests(self) -> tuple[ReportDeliveryRequest, ...]:
        """Return requests accepted by this no-op provider."""
        return tuple(self._requests)

    def deliver(self, request: ReportDeliveryRequest) -> ReportDeliveryResult:
        """Record the request and return a deterministic result without sending."""
        self._requests.append(request)
        if self._fail_with is not None:
            return ReportDeliveryResult.failed(
                provider_name=self.provider_name,
                error_message=self._fail_with,
            )
        return ReportDeliveryResult.delivered(
            provider_name=self.provider_name,
            message_id=self._message_id,
        )


class ReportDeliveryService:
    """Application service for report delivery through a provider interface."""

    def __init__(self, provider: ReportDeliveryProvider) -> None:
        self._provider = provider

    def deliver(self, request: ReportDeliveryRequest) -> ReportDeliveryResult:
        """Deliver a prepared request and return a provider-neutral result."""
        try:
            return self._provider.deliver(request)
        except Exception as exc:
            return ReportDeliveryResult.failed(
                provider_name=_provider_name(self._provider),
                error_message=str(exc) or exc.__class__.__name__,
            )

    def deliver_report(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
        content_type: str = "text/plain",
        metadata: Mapping[str, str] | None = None,
    ) -> ReportDeliveryResult:
        """Build and deliver a report request."""
        return self.deliver(
            ReportDeliveryRequest(
                recipient=ReportRecipient(email=recipient_email),
                subject=subject,
                body=body,
                content_type=content_type,
                metadata=metadata or {},
            )
        )


def _provider_name(provider: ReportDeliveryProvider) -> str:
    try:
        return _required_text(provider.provider_name, "provider_name")
    except Exception:
        return provider.__class__.__name__


def _required_email(value: str) -> str:
    email = _required_text(value, "recipient email")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("recipient email must be a valid email address")
    return email


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_content_type(value: str) -> str:
    content_type = _required_text(value, "content_type").lower()
    if content_type not in {"text/plain", "text/html"}:
        raise ValueError("content_type must be text/plain or text/html")
    return content_type


def _normalize_metadata(metadata: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = str(key).strip()
        if normalized_key:
            normalized[normalized_key] = str(value).strip()
    return normalized


__all__ = [
    "NoOpReportDeliveryProvider",
    "ReportDeliveryProvider",
    "ReportDeliveryRequest",
    "ReportDeliveryResult",
    "ReportDeliveryService",
    "ReportDeliveryStatus",
    "ReportRecipient",
]
