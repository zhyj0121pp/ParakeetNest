"""Deterministic mock provider for Market Health Layer intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.health.models import (
    HealthComponentState,
    MarketHealthComponent,
)


class MockMarketHealthProvider:
    """Return injected or default market health components without external I/O."""

    def __init__(
        self,
        components: tuple[MarketHealthComponent, ...] | None = None,
    ) -> None:
        """Initialize the provider with optional fixed component fixtures."""
        self._components = components
        self.calls: list[tuple[str, date | None]] = []

    def get_market_health_components(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
    ) -> tuple[MarketHealthComponent, ...]:
        """Return injected inputs or deterministic sample health components."""
        self.calls.append((universe, as_of))

        if self._components is not None:
            return self._components

        return (
            MarketHealthComponent(
                name="economic_regime",
                state=HealthComponentState.POSITIVE,
                score=0.72,
                evidence=("Economic regime is supportive.",),
            ),
            MarketHealthComponent(
                name="risk",
                state=HealthComponentState.WARNING,
                score=0.40,
                evidence=("Risk conditions are elevated but contained.",),
            ),
            MarketHealthComponent(
                name="breadth",
                state=HealthComponentState.POSITIVE,
                score=0.68,
                evidence=("Participation is broad enough to support the trend.",),
            ),
            MarketHealthComponent(
                name="momentum",
                state=HealthComponentState.POSITIVE,
                score=0.74,
                evidence=("Market momentum remains constructive.",),
            ),
            MarketHealthComponent(
                name="sentiment",
                state=HealthComponentState.NEUTRAL,
                score=0.58,
                evidence=("Sentiment is constructive but not euphoric.",),
            ),
            MarketHealthComponent(
                name="sector_rotation",
                state=HealthComponentState.NEUTRAL,
                score=0.55,
                evidence=("Sector leadership is mixed but stable.",),
            ),
        )


__all__ = ["MockMarketHealthProvider"]
