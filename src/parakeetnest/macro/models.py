"""Provider-agnostic Macro Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class MacroCategory(str, Enum):
    """Common provider-independent macroeconomic indicator categories."""

    GROWTH = "growth"
    INFLATION = "inflation"
    LABOR = "labor"
    RATES = "rates"
    CREDIT = "credit"
    HOUSING = "housing"
    CONSUMER = "consumer"
    TRADE = "trade"
    FISCAL = "fiscal"
    MONEY = "money"
    SENTIMENT = "sentiment"
    OTHER = "other"


class MacroFrequency(str, Enum):
    """Supported provider-neutral macroeconomic observation frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"


class MacroUnit(str, Enum):
    """Common provider-independent units for macroeconomic values."""

    INDEX = "index"
    PERCENT = "percent"
    PERCENTAGE_POINT = "percentage_point"
    BASIS_POINT = "basis_point"
    CURRENCY = "currency"
    CURRENCY_PER_UNIT = "currency_per_unit"
    PERSONS = "persons"
    COUNT = "count"
    THOUSANDS = "thousands"
    MILLIONS = "millions"
    BILLIONS = "billions"
    RATIO = "ratio"
    OTHER = "other"


@dataclass(frozen=True)
class MacroIndicator:
    """Normalized macroeconomic indicator metadata from any provider."""

    indicator_id: str
    name: str
    category: MacroCategory
    frequency: MacroFrequency
    unit: MacroUnit
    region: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Normalize stable metadata and validate enum fields."""
        object.__setattr__(self, "indicator_id", self.indicator_id.strip().lower())
        object.__setattr__(self, "name", self.name.strip())
        if not isinstance(self.category, MacroCategory):
            object.__setattr__(self, "category", MacroCategory(self.category))
        if not isinstance(self.frequency, MacroFrequency):
            object.__setattr__(self, "frequency", MacroFrequency(self.frequency))
        if not isinstance(self.unit, MacroUnit):
            object.__setattr__(self, "unit", MacroUnit(self.unit))
        if self.region is not None:
            object.__setattr__(self, "region", self.region.strip().upper())
        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True)
class MacroObservation:
    """A single provider-neutral observation for a macroeconomic period."""

    period: date
    value: float | None
    released_at: datetime | None = None
    revised_at: datetime | None = None


@dataclass(frozen=True)
class MacroSeries:
    """Ordered observations for one macroeconomic indicator."""

    indicator: MacroIndicator
    observations: list[MacroObservation] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Keep observations in chronological order for stable consumers."""
        object.__setattr__(
            self,
            "observations",
            sorted(self.observations, key=lambda observation: observation.period),
        )


@dataclass(frozen=True)
class MacroSnapshot:
    """Point-in-time collection of macroeconomic series for research context."""

    as_of_date: date
    series: list[MacroSeries] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize snapshot metadata without adding provider coupling."""
        object.__setattr__(
            self,
            "series",
            sorted(self.series, key=lambda item: item.indicator.indicator_id),
        )
        object.__setattr__(self, "notes", _clean_strings(self.notes))


def _clean_strings(values: list[str]) -> list[str]:
    """Remove blank strings while preserving source order."""
    return [value.strip() for value in values if value.strip()]


__all__ = [
    "MacroCategory",
    "MacroFrequency",
    "MacroIndicator",
    "MacroObservation",
    "MacroSeries",
    "MacroSnapshot",
    "MacroUnit",
]
