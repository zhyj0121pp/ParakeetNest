"""Provider abstractions for Sector Rotation intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.sector_rotation.models import (
    MomentumSignal,
    RelativeStrengthSignal,
    SectorIdentifier,
    SectorPerformance,
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)


class SectorRotationProvider(Protocol):
    """Provider-neutral contract for sector rotation snapshots."""

    def get_sector_rotation_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return a normalized sector rotation snapshot."""


class MockSectorRotationProvider:
    """Deterministic network-free provider for tests and local development."""

    def __init__(self, snapshot: SectorRotationSnapshot | None = None) -> None:
        self._snapshot = snapshot
        self.calls: list[date | None] = []

    def get_sector_rotation_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return the injected snapshot or deterministic neutral sample data."""
        self.calls.append(as_of_date)
        if self._snapshot is not None:
            return self._snapshot

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
        return SectorRotationSnapshot(
            as_of_date=observed_on,
            signals=[
                SectorRotationSignal(
                    sector=technology,
                    classification=SectorRotationClassification.NEUTRAL,
                    relative_strength=RelativeStrengthSignal(
                        sector=technology,
                        score=0.0,
                        rank=1,
                        benchmark="broad_market",
                        interpretation="No live market data connected.",
                    ),
                    momentum=MomentumSignal(
                        sector=technology,
                        score=0.0,
                        direction="flat",
                        window_days=63,
                        interpretation="Deterministic mock momentum.",
                    ),
                    performance=SectorPerformance(
                        sector=technology,
                        period_return=0.0,
                        benchmark_return=0.0,
                        relative_return=0.0,
                        as_of_date=observed_on,
                        window_days=63,
                    ),
                    confidence="unknown",
                    evidence=("Mock provider uses deterministic neutral data.",),
                ),
                SectorRotationSignal(
                    sector=utilities,
                    classification=SectorRotationClassification.NEUTRAL,
                    relative_strength=RelativeStrengthSignal(
                        sector=utilities,
                        score=0.0,
                        rank=2,
                        benchmark="broad_market",
                        interpretation="No live market data connected.",
                    ),
                    momentum=MomentumSignal(
                        sector=utilities,
                        score=0.0,
                        direction="flat",
                        window_days=63,
                        interpretation="Deterministic mock momentum.",
                    ),
                    performance=SectorPerformance(
                        sector=utilities,
                        period_return=0.0,
                        benchmark_return=0.0,
                        relative_return=0.0,
                        as_of_date=observed_on,
                        window_days=63,
                    ),
                    confidence="unknown",
                    evidence=("Mock provider uses deterministic neutral data.",),
                ),
            ],
            summary="Deterministic mock sector rotation snapshot.",
            source="mock_sector_rotation_provider",
        )


__all__ = ["MockSectorRotationProvider", "SectorRotationProvider"]

