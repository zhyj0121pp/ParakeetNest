"""Deterministic mock macro data service."""

from datetime import date

from parakeetnest.domain import MacroSnapshot
from parakeetnest.services.base import MockDataService, ServiceResult
from parakeetnest.services.portfolio import MOCK_FETCHED_AT


class MockMacroService(MockDataService[MacroSnapshot]):
    """Return deterministic macro snapshots without FRED access."""

    name = "mock_macro"

    def collect(self) -> tuple[ServiceResult[MacroSnapshot], ...]:
        """Collect deterministic macro snapshots."""
        snapshots = (
            MacroSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                indicator="fed_funds_rate",
                value=4.75,
                unit="percent",
                observed_on=date(2026, 6, 29),
            ),
            MacroSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                indicator="cpi_yoy",
                value=2.8,
                unit="percent",
                observed_on=date(2026, 6, 29),
            ),
        )
        return tuple(self._result(snapshot) for snapshot in snapshots)
