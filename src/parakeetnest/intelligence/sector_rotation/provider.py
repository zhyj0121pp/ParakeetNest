"""Provider abstractions for Sector Rotation intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.sector_rotation.models import (
    SectorIdentifier,
    SectorPerformance,
)


class SectorRotationProvider(Protocol):
    """Provider-neutral contract for sector performance facts."""

    def get_sector_performance(
        self,
        *,
        as_of_date: date | None = None,
    ) -> list[SectorPerformance]:
        """Return normalized sector performance evidence."""


class MockSectorRotationProvider:
    """Deterministic network-free provider for tests and local development."""

    def __init__(self, performance: list[SectorPerformance] | None = None) -> None:
        self._performance = performance
        self.calls: list[date | None] = []

    def get_sector_performance(
        self,
        *,
        as_of_date: date | None = None,
    ) -> list[SectorPerformance]:
        """Return injected performance or deterministic sample facts."""
        self.calls.append(as_of_date)
        if self._performance is not None:
            return self._performance

        observed_on = as_of_date or date.today()
        technology = SectorIdentifier(
            sector_id="technology",
            name="Technology",
            taxonomy="standard_sector",
        )
        utilities = SectorIdentifier(
            sector_id="utilities",
            name="Utilities",
            taxonomy="standard_sector",
        )
        return [
            SectorPerformance(
                sector=technology,
                period_return=0.0,
                benchmark_return=0.0,
                relative_return=0.0,
                as_of_date=observed_on,
                window_days=63,
            ),
            SectorPerformance(
                sector=utilities,
                period_return=0.0,
                benchmark_return=0.0,
                relative_return=0.0,
                as_of_date=observed_on,
                window_days=63,
            ),
        ]


__all__ = ["MockSectorRotationProvider", "SectorRotationProvider"]
