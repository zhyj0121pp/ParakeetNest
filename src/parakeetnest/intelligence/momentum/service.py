"""Service boundary for provider-neutral Momentum Layer intelligence.

The service is orchestration only: it asks an injected provider for raw inputs,
passes those inputs to an injected calculator, and returns the calculator's
snapshot unchanged.
"""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.momentum.calculator import MomentumCalculator
from parakeetnest.intelligence.momentum.models import MomentumSnapshot
from parakeetnest.intelligence.momentum.provider import MomentumProvider


class MomentumService:
    """Public application boundary for momentum snapshots."""

    def __init__(
        self,
        provider: MomentumProvider,
        calculator: MomentumCalculator,
    ) -> None:
        """Initialize the service with explicit provider and calculator dependencies."""
        self._provider = provider
        self._calculator = calculator

    def get_snapshot(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumSnapshot:
        """Return a provider-neutral momentum snapshot for the requested symbol."""
        inputs = self._provider.get_momentum_inputs(symbol, as_of=as_of)
        return self._calculator.calculate(inputs)


__all__ = ["MomentumService"]
