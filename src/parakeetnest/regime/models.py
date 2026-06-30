"""Provider-agnostic Economic Regime domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class EconomicRegime(str, Enum):
    """Common provider-independent economic regime classifications."""

    EXPANSION = "expansion"
    SLOWDOWN = "slowdown"
    RECESSION = "recession"
    RECOVERY = "recovery"
    STAGFLATION = "stagflation"
    DISINFLATIONARY_GROWTH = "disinflationary_growth"
    OVERHEATING = "overheating"
    UNKNOWN = "unknown"


class RegimeSignal(str, Enum):
    """Provider-neutral signal families used to explain a regime view."""

    GROWTH = "growth"
    INFLATION = "inflation"
    LABOR = "labor"
    RATES = "rates"
    CREDIT = "credit"
    LIQUIDITY = "liquidity"
    CONSUMER = "consumer"
    FISCAL = "fiscal"
    SENTIMENT = "sentiment"
    OTHER = "other"


class RegimeConfidence(str, Enum):
    """Confidence level for economic regime snapshots."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RegimeIndicator:
    """Provider-neutral indicator used as evidence for a regime view."""

    signal: RegimeSignal
    name: str
    value: float | None = None
    unit: str | None = None
    as_of_date: date | None = None
    interpretation: str | None = None

    def __post_init__(self) -> None:
        """Normalize stable metadata and validate enum fields."""
        if not isinstance(self.signal, RegimeSignal):
            object.__setattr__(self, "signal", RegimeSignal(self.signal))
        object.__setattr__(self, "name", self.name.strip())
        if self.unit is not None:
            object.__setattr__(self, "unit", self.unit.strip())
        if self.interpretation is not None:
            object.__setattr__(self, "interpretation", self.interpretation.strip())


@dataclass(frozen=True)
class EconomicRegimeSnapshot:
    """Point-in-time provider-neutral economic regime assessment."""

    regime: EconomicRegime
    confidence: RegimeConfidence
    as_of_date: date
    indicators: list[RegimeIndicator] = field(default_factory=list)
    summary: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        """Normalize snapshot metadata without adding provider coupling."""
        if not isinstance(self.regime, EconomicRegime):
            object.__setattr__(self, "regime", EconomicRegime(self.regime))
        if not isinstance(self.confidence, RegimeConfidence):
            object.__setattr__(
                self,
                "confidence",
                RegimeConfidence(self.confidence),
            )
        object.__setattr__(
            self,
            "indicators",
            sorted(self.indicators, key=lambda indicator: indicator.name.lower()),
        )
        if self.summary is not None:
            object.__setattr__(self, "summary", self.summary.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


__all__ = [
    "EconomicRegime",
    "EconomicRegimeSnapshot",
    "RegimeConfidence",
    "RegimeIndicator",
    "RegimeSignal",
]
