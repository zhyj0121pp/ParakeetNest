"""Service boundary for provider-neutral Risk Layer intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.risk.calculator import RiskCalculator
from parakeetnest.intelligence.risk.models import RiskAssessment
from parakeetnest.intelligence.risk.provider import RiskProvider


class RiskService:
    """Public service layer for aggregate risk assessments."""

    def __init__(
        self,
        provider: RiskProvider,
        calculator: RiskCalculator,
    ) -> None:
        """Initialize the service with provider and calculator abstractions."""
        self._provider = provider
        self._calculator = calculator

    def get_risk_assessment(
        self,
        *,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        """Return a provider-neutral risk assessment."""
        signals = self._provider.get_risk_signals(as_of_date=as_of_date)
        return self._calculator.calculate(signals, as_of_date=as_of_date)


__all__ = ["RiskService"]
