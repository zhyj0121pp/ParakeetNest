"""Service boundary for provider-neutral Market Breadth intelligence."""

from __future__ import annotations

from dataclasses import replace

from parakeetnest.intelligence.market_breadth.calculator import (
    MarketBreadthCalculator,
)
from parakeetnest.intelligence.market_breadth.models import MarketBreadthSnapshot
from parakeetnest.intelligence.market_breadth.provider import MarketBreadthProvider


class MarketBreadthService:
    """Public service layer for market breadth snapshots."""

    def __init__(
        self,
        provider: MarketBreadthProvider,
        calculator: MarketBreadthCalculator | None = None,
    ) -> None:
        """Initialize the service with provider and calculator abstractions."""
        self._provider = provider
        self._calculator = calculator or MarketBreadthCalculator()

    def get_market_breadth(
        self,
        universe: str,
    ) -> MarketBreadthSnapshot:
        """Return a provider-neutral market breadth snapshot."""
        snapshot = self._provider.get_breadth_snapshot(universe)
        breadth_score = self._calculator.calculate_score(snapshot)
        breadth_regime = self._calculator.classify(breadth_score)

        return replace(
            snapshot,
            breadth_score=breadth_score,
            breadth_regime=breadth_regime,
        )


__all__ = ["MarketBreadthService"]
