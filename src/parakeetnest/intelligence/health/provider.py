"""Provider abstractions for Market Health Layer intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.health.models import MarketHealthComponent


class MarketHealthProvider(Protocol):
    """Provider-neutral contract for retrieving market health components."""

    def get_market_health_components(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
    ) -> tuple[MarketHealthComponent, ...]:
        """Return provider-neutral component facts for aggregate health scoring."""


__all__ = ["MarketHealthProvider"]
