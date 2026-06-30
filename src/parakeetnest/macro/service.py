"""Provider-agnostic macro data service boundary."""

from __future__ import annotations

from datetime import date

from parakeetnest.macro.models import (
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
)
from parakeetnest.macro.provider import MacroDataProvider


class MacroDataService:
    """Single entry point for provider-backed macro data lookups."""

    def __init__(self, provider: MacroDataProvider) -> None:
        """Initialize the service with one macro data provider."""
        self._provider = provider

    def get_series(
        self,
        indicator_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MacroSeries:
        """Return provider-backed macro series for the indicator."""
        return self._provider.get_series(indicator_id, start_date, end_date)

    def get_latest(self, indicator_id: str) -> MacroObservation | None:
        """Return the latest provider-backed macro observation."""
        return self._provider.get_latest(indicator_id)

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Return a provider-backed macro snapshot for the indicators."""
        return self._provider.get_snapshot(indicator_ids, as_of_date)


__all__ = ["MacroDataService"]
