"""Service boundary for provider-neutral Sector Rotation intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.sector_rotation.calculator import (
    SectorRotationCalculator,
)
from parakeetnest.intelligence.sector_rotation.models import SectorRotationSnapshot
from parakeetnest.intelligence.sector_rotation.provider import SectorRotationProvider


class SectorRotationService:
    """Public service layer for sector rotation snapshots."""

    def __init__(
        self,
        provider: SectorRotationProvider,
        calculator: SectorRotationCalculator | None = None,
    ) -> None:
        """Initialize the service with provider and calculator abstractions."""
        self._provider = provider
        self._calculator = calculator or SectorRotationCalculator()

    def get_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return a provider-neutral sector rotation snapshot."""
        sector_performance = self._provider.get_sector_performance(
            as_of_date=as_of_date
        )
        return self._calculator.calculate(
            sector_performance,
            as_of_date=as_of_date,
        )


__all__ = ["SectorRotationService"]
