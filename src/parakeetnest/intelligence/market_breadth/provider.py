"""Provider abstractions for Market Breadth intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.market_breadth.models import (
    BreadthRegime,
    MarketBreadthSnapshot,
)


class MarketBreadthProvider(Protocol):
    """Provider-neutral contract for normalized breadth snapshots."""

    def get_breadth_snapshot(self, universe: str) -> MarketBreadthSnapshot:
        """Return a normalized market breadth snapshot for a universe."""


class MockMarketBreadthProvider:
    """Deterministic network-free provider for tests and local development."""

    def __init__(self, snapshot: MarketBreadthSnapshot | None = None) -> None:
        self._snapshot = snapshot
        self.calls: list[str] = []

    def get_breadth_snapshot(self, universe: str) -> MarketBreadthSnapshot:
        """Return an injected snapshot or deterministic sample breadth data."""
        self.calls.append(universe)
        if self._snapshot is not None:
            return self._snapshot

        return MarketBreadthSnapshot(
            universe=universe,
            date=date(2026, 6, 30),
            advancers=312,
            decliners=180,
            unchanged=8,
            new_highs=42,
            new_lows=15,
            percent_above_20d_ma=62.4,
            percent_above_50d_ma=58.1,
            percent_above_200d_ma=54.7,
            up_volume=4_200_000_000,
            down_volume=2_900_000_000,
            breadth_score=0.64,
            breadth_regime=BreadthRegime.HEALTHY,
            warnings=(),
        )


__all__ = ["MarketBreadthProvider", "MockMarketBreadthProvider"]
