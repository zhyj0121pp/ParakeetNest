"""Provider-neutral contract for macroeconomic data integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from parakeetnest.macro.models import (
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
)


class MacroDataProvider(ABC):
    """Abstract interface for provider-neutral macroeconomic data sources."""

    @abstractmethod
    def get_series(
        self,
        indicator_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MacroSeries:
        """Return a normalized macroeconomic series for the requested period."""

    @abstractmethod
    def get_latest(self, indicator_id: str) -> MacroObservation | None:
        """Return the latest normalized observation when one is available."""

    @abstractmethod
    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Return a point-in-time snapshot for the requested indicators."""


__all__ = ["MacroDataProvider"]
