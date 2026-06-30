"""Provider-neutral valuation service boundary."""

from __future__ import annotations

from parakeetnest.valuation.calculator import ValuationCalculator
from parakeetnest.valuation.models import ValuationInput, ValuationSnapshot


class ValuationService:
    """Single entry point for producing valuation snapshots."""

    def __init__(self, calculator: ValuationCalculator | None = None) -> None:
        """Initialize the service with a valuation calculator."""
        self._calculator = calculator or ValuationCalculator()

    def create_snapshot(self, valuation_input: ValuationInput) -> ValuationSnapshot:
        """Create a valuation snapshot from normalized valuation inputs."""
        return self._calculator.calculate(valuation_input)


__all__ = ["ValuationService"]
