"""Deterministic mock financial data service."""

from parakeetnest.domain import FinancialSnapshot
from parakeetnest.services.base import MockDataService, ServiceResult
from parakeetnest.services.portfolio import MOCK_FETCHED_AT


class MockFinancialService(MockDataService[FinancialSnapshot]):
    """Return deterministic financial snapshots without provider access."""

    name = "mock_financial"

    def collect(self) -> tuple[ServiceResult[FinancialSnapshot], ...]:
        """Collect deterministic financial snapshots."""
        snapshots = (
            FinancialSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="NVDA",
                period="FY2026",
                revenue=130_000_000_000.0,
                eps=13.5,
                gross_margin=0.74,
                operating_margin=0.62,
                free_cash_flow=58_000_000_000.0,
            ),
            FinancialSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="TSLA",
                period="FY2026",
                revenue=98_000_000_000.0,
                eps=4.2,
                gross_margin=0.19,
                operating_margin=0.08,
                free_cash_flow=6_500_000_000.0,
            ),
        )
        return tuple(self._result(snapshot) for snapshot in snapshots)


FinancialService = MockFinancialService
