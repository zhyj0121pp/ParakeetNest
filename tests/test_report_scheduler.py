"""Tests for manual daily report scheduling."""

from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from parakeetnest.research import (
    DailyReportDeliveryRequest,
    ReportDeliveryResult,
    ReportDeliveryStatus,
    ReportSchedule,
    ReportScheduleFrequency,
    ReportScheduler,
    ScheduledReportRunStatus,
)


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


class FakeDailyReportDeliveryService:
    def __init__(self, result: ReportDeliveryResult) -> None:
        self.result = result
        self.requests: list[DailyReportDeliveryRequest] = []

    def deliver(self, request: DailyReportDeliveryRequest) -> ReportDeliveryResult:
        self.requests.append(request)
        return self.result


def test_can_create_daily_report_schedule() -> None:
    schedule = ReportSchedule(
        tickers=[" nvda ", "aapl"],
        recipient_email=" investor@example.com ",
        account_id=" main ",
        time_of_day=time(8, 30),
        timezone=" America/Los_Angeles ",
        metadata={" run_type ": " daily ", " ": "ignored"},
    )

    assert schedule.frequency is ReportScheduleFrequency.DAILY
    assert schedule.tickers == ("NVDA", "AAPL")
    assert schedule.recipient_email == "investor@example.com"
    assert schedule.account_id == "main"
    assert schedule.time_of_day == time(8, 30)
    assert schedule.timezone == "America/Los_Angeles"
    assert schedule.metadata == {"run_type": "daily"}


def test_scheduler_manually_triggers_successful_delivery() -> None:
    delivery_result = ReportDeliveryResult.delivered(
        provider_name="fake",
        message_id="daily-123",
    )
    delivery_service = FakeDailyReportDeliveryService(delivery_result)
    scheduler = ReportScheduler(delivery_service)
    schedule = ReportSchedule(
        tickers=("NVDA", "AAPL"),
        recipient_email="investor@example.com",
        account_id="main",
        metadata={"source": "scheduler"},
    )

    run = scheduler.run_once(schedule, generated_at=GENERATED_AT)

    assert run.schedule is schedule
    assert run.generated_at == GENERATED_AT
    assert run.status is ScheduledReportRunStatus.DELIVERED
    assert run.delivery_result is delivery_result
    assert delivery_service.requests == [
        DailyReportDeliveryRequest(
            tickers=("NVDA", "AAPL"),
            recipient_email="investor@example.com",
            account_id="main",
            generated_at=GENERATED_AT,
            metadata={"source": "scheduler"},
        )
    ]


def test_scheduler_returns_failed_run_for_failed_delivery_result() -> None:
    delivery_result = ReportDeliveryResult.failed(
        provider_name="fake",
        error_message="simulated delivery failure",
    )
    delivery_service = FakeDailyReportDeliveryService(delivery_result)
    scheduler = ReportScheduler(delivery_service)
    schedule = ReportSchedule(
        tickers=("NVDA",),
        recipient_email="investor@example.com",
    )

    run = scheduler.run_once(schedule, generated_at=GENERATED_AT)

    assert run.status is ScheduledReportRunStatus.FAILED
    assert run.delivery_result.status is ReportDeliveryStatus.FAILED
    assert run.delivery_result.error_message == "simulated delivery failure"


def test_schedule_validates_required_inputs() -> None:
    with pytest.raises(ValueError, match="tickers are required"):
        ReportSchedule(tickers=[], recipient_email="investor@example.com")

    with pytest.raises(ValueError, match="valid email"):
        ReportSchedule(tickers=("NVDA",), recipient_email="not-an-email")
