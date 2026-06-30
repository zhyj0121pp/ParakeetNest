"""Service boundary for provider-neutral Sector Rotation intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.sector_rotation.models import SectorRotationSnapshot
from parakeetnest.intelligence.sector_rotation.provider import SectorRotationProvider


class SectorRotationService:
    """Public service layer for sector rotation snapshots."""

    def __init__(self, provider: SectorRotationProvider) -> None:
        """Initialize the service with a provider abstraction."""
        self._provider = provider

    def get_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return a provider-neutral sector rotation snapshot."""
        return self._provider.get_sector_rotation_snapshot(as_of_date=as_of_date)


__all__ = ["SectorRotationService"]

