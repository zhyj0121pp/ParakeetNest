"""Service boundary for provider-neutral Momentum Layer intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.momentum.calculator import MomentumCalculator
from parakeetnest.intelligence.momentum.models import MomentumSnapshot
from parakeetnest.intelligence.momentum.provider import MomentumProvider


class MomentumService:
    """Public service layer for momentum snapshots."""

    def __init__(
        self,
        provider: MomentumProvider,
        calculator: MomentumCalculator,
    ) -> None:
        """Initialize the service with provider and calculator abstractions."""
        self._provider = provider
        self._calculator = calculator

    def get_snapshot(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumSnapshot:
        """Return a provider-neutral momentum snapshot."""
        inputs = self._provider.get_momentum_inputs(symbol, as_of=as_of)
        return self._calculator.calculate(inputs)


__all__ = ["MomentumService"]
