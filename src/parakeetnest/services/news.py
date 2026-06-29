"""Deterministic mock news service."""

from parakeetnest.domain import NewsSnapshot
from parakeetnest.services.base import MockDataService, ServiceResult
from parakeetnest.services.portfolio import MOCK_FETCHED_AT


class MockNewsService(MockDataService[NewsSnapshot]):
    """Return deterministic news snapshots without news provider access."""

    name = "mock_news"

    def collect(self) -> tuple[ServiceResult[NewsSnapshot], ...]:
        """Collect deterministic news snapshots."""
        snapshots = (
            NewsSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="NVDA",
                title="Mock AI infrastructure demand remains resilient",
                summary="Deterministic placeholder news for local testing.",
                published_at=MOCK_FETCHED_AT,
            ),
            NewsSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="TSLA",
                title="Mock vehicle delivery expectations stay in focus",
                summary="Deterministic placeholder news for local testing.",
                published_at=MOCK_FETCHED_AT,
            ),
        )
        return tuple(self._result(snapshot) for snapshot in snapshots)
