"""Deterministic mock market data service."""

from parakeetnest.domain import MarketSnapshot
from parakeetnest.services.base import MockDataService, ServiceResult
from parakeetnest.services.portfolio import MOCK_FETCHED_AT


class MockMarketDataService(MockDataService[MarketSnapshot]):
    """Return deterministic market snapshots without market data access."""

    name = "mock_market_data"

    def collect(self) -> tuple[ServiceResult[MarketSnapshot], ...]:
        """Collect deterministic market snapshots."""
        snapshots = (
            MarketSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="NVDA",
                price=920.0,
                daily_change=12.5,
                volume=42_000_000.0,
                market_cap=2_260_000_000_000.0,
                pe_ratio=68.0,
                eps=13.5,
            ),
            MarketSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="TSLA",
                price=230.0,
                daily_change=-3.2,
                volume=88_000_000.0,
                market_cap=735_000_000_000.0,
                pe_ratio=55.0,
                eps=4.2,
            ),
        )
        return tuple(self._result(snapshot) for snapshot in snapshots)


MarketDataService = MockMarketDataService
