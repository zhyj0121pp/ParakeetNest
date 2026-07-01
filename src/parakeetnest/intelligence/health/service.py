"""Service boundary for provider-neutral Market Health Layer intelligence."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from parakeetnest.intelligence.health.calculator import MarketHealthCalculator
from parakeetnest.intelligence.health.models import MarketHealthSnapshot
from parakeetnest.intelligence.health.provider import MarketHealthProvider


class MarketHealthService:
    """Public application boundary for market health snapshots."""

    def __init__(
        self,
        provider: MarketHealthProvider,
        calculator: MarketHealthCalculator,
    ) -> None:
        """Initialize the service with explicit provider and calculator dependencies."""
        self._provider = provider
        self._calculator = calculator

    def get_market_health(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MarketHealthSnapshot:
        """Return a provider-neutral market health snapshot."""
        observed_on = as_of or date.today()
        components = self._provider.get_market_health_components(
            universe=universe,
            as_of=as_of,
        )
        return self._calculator.calculate(
            as_of=observed_on,
            universe=universe,
            components=components,
            metadata=metadata,
        )


__all__ = ["MarketHealthService"]
