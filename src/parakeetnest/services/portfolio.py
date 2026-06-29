"""Deterministic mock portfolio service."""

from datetime import UTC, datetime

from parakeetnest.domain import HoldingSnapshot, PortfolioSnapshot
from parakeetnest.services.base import MockDataService, ServiceResult


MOCK_FETCHED_AT = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)


class MockPortfolioService(MockDataService[PortfolioSnapshot]):
    """Return deterministic portfolio snapshots without brokerage access."""

    name = "mock_portfolio"

    def collect(self) -> tuple[ServiceResult[PortfolioSnapshot], ...]:
        """Collect a deterministic portfolio snapshot."""
        snapshot = PortfolioSnapshot(
            source=self.name,
            fetched_at=MOCK_FETCHED_AT,
            holdings=(
                HoldingSnapshot(
                    symbol="NVDA",
                    quantity=2.0,
                    cost_basis=820.0,
                    market_value=1840.0,
                    unrealized_pl=200.0,
                ),
                HoldingSnapshot(
                    symbol="TSLA",
                    quantity=3.0,
                    cost_basis=210.0,
                    market_value=690.0,
                    unrealized_pl=60.0,
                ),
            ),
            cash_balance=1500.0,
        )
        return (self._result(snapshot),)


PortfolioService = MockPortfolioService
