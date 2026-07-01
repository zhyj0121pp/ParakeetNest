"""Manual scheduler abstraction for daily investment report delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from enum import StrEnum
from typing import Mapping, Protocol

from parakeetnest.research.daily_delivery import DailyReportDeliveryRequest
from parakeetnest.research.delivery import (
    ReportDeliveryResult,
    ReportDeliveryStatus,
)


class ReportScheduleFrequency(StrEnum):
    """Provider-neutral report schedule cadence."""

    DAILY = "daily"


class ScheduledReportRunStatus(StrEnum):
    """Outcome of one scheduled report run."""

    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass(frozen=True)
class ReportSchedule:
    """Provider-neutral schedule for a recurring investment report."""

    tickers: tuple[str, ...] | list[str]
    recipient_email: str
    frequency: ReportScheduleFrequency = ReportScheduleFrequency.DAILY
    account_id: str | None = None
    time_of_day: time | None = None
    timezone: str | None = None
    metadata: Mapping[str, str] | None = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.frequency, ReportScheduleFrequency):
            object.__setattr__(
                self,
                "frequency",
                ReportScheduleFrequency(self.frequency),
            )
        object.__setattr__(self, "tickers", _normalize_tickers(self.tickers))
        object.__setattr__(
            self,
            "recipient_email",
            _required_email(self.recipient_email),
        )
        object.__setattr__(self, "account_id", _optional_text(self.account_id))
        object.__setattr__(self, "timezone", _optional_text(self.timezone))
        object.__setattr__(
            self,
            "metadata",
            _normalize_metadata(self.metadata or {}),
        )


@dataclass(frozen=True)
class ScheduledReportRun:
    """Result of manually triggering one report schedule."""

    schedule: ReportSchedule
    generated_at: datetime
    status: ScheduledReportRunStatus
    delivery_result: ReportDeliveryResult

    def __post_init__(self) -> None:
        generated_at = self.generated_at
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)
        object.__setattr__(self, "generated_at", generated_at)
        if not isinstance(self.status, ScheduledReportRunStatus):
            object.__setattr__(self, "status", ScheduledReportRunStatus(self.status))


class _DailyReportDeliveryService(Protocol):
    def deliver(self, request: DailyReportDeliveryRequest) -> ReportDeliveryResult:
        """Compose and deliver a daily report."""


class ReportScheduler:
    """Manual scheduler facade for report delivery use cases."""

    def __init__(self, delivery_service: _DailyReportDeliveryService) -> None:
        self._delivery_service = delivery_service

    def run_once(
        self,
        schedule: ReportSchedule,
        generated_at: datetime | None = None,
    ) -> ScheduledReportRun:
        """Trigger one scheduled daily report delivery now."""
        run_generated_at = generated_at or datetime.now(UTC)
        delivery_result = self._delivery_service.deliver(
            DailyReportDeliveryRequest(
                tickers=schedule.tickers,
                recipient_email=schedule.recipient_email,
                account_id=schedule.account_id,
                generated_at=run_generated_at,
                metadata=schedule.metadata,
            )
        )
        return ScheduledReportRun(
            schedule=schedule,
            generated_at=run_generated_at,
            status=_run_status_from_delivery(delivery_result),
            delivery_result=delivery_result,
        )


def _run_status_from_delivery(
    delivery_result: ReportDeliveryResult,
) -> ScheduledReportRunStatus:
    if delivery_result.status is ReportDeliveryStatus.DELIVERED:
        return ScheduledReportRunStatus.DELIVERED
    return ScheduledReportRunStatus.FAILED


def _normalize_tickers(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    tickers = tuple(
        str(value).strip().upper() for value in values if str(value).strip()
    )
    if not tickers:
        raise ValueError("tickers are required")
    return tickers


def _required_email(value: str) -> str:
    email = _required_text(value, "recipient_email")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("recipient_email must be a valid email address")
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


def _normalize_metadata(metadata: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = str(key).strip()
        if normalized_key:
            normalized[normalized_key] = str(value).strip()
    return normalized


__all__ = [
    "ReportSchedule",
    "ReportScheduleFrequency",
    "ReportScheduler",
    "ScheduledReportRun",
    "ScheduledReportRunStatus",
]
