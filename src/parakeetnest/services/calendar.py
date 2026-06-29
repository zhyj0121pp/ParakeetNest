"""Deterministic mock calendar service."""

from datetime import UTC, datetime

from parakeetnest.domain import CalendarSnapshot
from parakeetnest.services.base import MockDataService, ServiceResult
from parakeetnest.services.portfolio import MOCK_FETCHED_AT


class MockCalendarService(MockDataService[CalendarSnapshot]):
    """Return deterministic calendar snapshots without external access."""

    name = "mock_calendar"

    def collect(self) -> tuple[ServiceResult[CalendarSnapshot], ...]:
        """Collect deterministic calendar event snapshots."""
        snapshots = (
            CalendarSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                event_type="earnings",
                title="NVDA mock earnings date",
                symbol="NVDA",
                event_at=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
            ),
            CalendarSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                event_type="macro",
                title="Mock CPI release",
                event_at=datetime(2026, 7, 14, 12, 30, tzinfo=UTC),
            ),
        )
        return tuple(self._result(snapshot) for snapshot in snapshots)
