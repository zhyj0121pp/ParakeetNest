"""Provider-neutral Sector Rotation domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class SectorRotationClassification(str, Enum):
    """Provider-independent sector rotation classifications."""

    LEADING = "leading"
    IMPROVING = "improving"
    WEAKENING = "weakening"
    LAGGING = "lagging"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SectorIdentifier:
    """Stable sector identity independent from data-source symbols."""

    sector_id: str
    name: str
    taxonomy: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "sector_id", self.sector_id.strip().lower())
        object.__setattr__(self, "name", self.name.strip())
        if self.taxonomy is not None:
            object.__setattr__(self, "taxonomy", self.taxonomy.strip())


@dataclass(frozen=True)
class SectorPerformance:
    """Point-in-time sector performance evidence."""

    sector: SectorIdentifier
    period_return: float | None = None
    benchmark_return: float | None = None
    relative_return: float | None = None
    as_of_date: date | None = None
    window_days: int | None = None


@dataclass(frozen=True)
class RelativeStrengthSignal:
    """Provider-neutral relative strength evidence for one sector."""

    sector: SectorIdentifier
    score: float | None = None
    rank: int | None = None
    benchmark: str | None = None
    interpretation: str | None = None

    def __post_init__(self) -> None:
        if self.benchmark is not None:
            object.__setattr__(self, "benchmark", self.benchmark.strip())
        if self.interpretation is not None:
            object.__setattr__(
                self,
                "interpretation",
                self.interpretation.strip(),
            )


@dataclass(frozen=True)
class MomentumSignal:
    """Provider-neutral momentum evidence for one sector."""

    sector: SectorIdentifier
    score: float | None = None
    direction: str | None = None
    window_days: int | None = None
    interpretation: str | None = None

    def __post_init__(self) -> None:
        if self.direction is not None:
            object.__setattr__(self, "direction", self.direction.strip().lower())
        if self.interpretation is not None:
            object.__setattr__(
                self,
                "interpretation",
                self.interpretation.strip(),
            )


@dataclass(frozen=True)
class SectorRotationSignal:
    """Combined rotation signal for one sector."""

    sector: SectorIdentifier
    classification: SectorRotationClassification
    relative_strength: RelativeStrengthSignal | None = None
    momentum: MomentumSignal | None = None
    performance: SectorPerformance | None = None
    confidence: str = "unknown"
    evidence: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    catalysts: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.classification, SectorRotationClassification):
            object.__setattr__(
                self,
                "classification",
                SectorRotationClassification(self.classification),
            )
        object.__setattr__(self, "confidence", self.confidence.strip().lower())
        object.__setattr__(
            self,
            "evidence",
            tuple(item.strip() for item in self.evidence if item.strip()),
        )
        object.__setattr__(
            self,
            "risks",
            tuple(item.strip() for item in self.risks if item.strip()),
        )
        object.__setattr__(
            self,
            "catalysts",
            tuple(item.strip() for item in self.catalysts if item.strip()),
        )


@dataclass(frozen=True)
class SectorRotationSnapshot:
    """Point-in-time sector rotation intelligence snapshot."""

    as_of_date: date
    signals: list[SectorRotationSignal] = field(default_factory=list)
    summary: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "signals",
            sorted(self.signals, key=lambda signal: signal.sector.name.lower()),
        )
        if self.summary is not None:
            object.__setattr__(self, "summary", self.summary.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


__all__ = [
    "MomentumSignal",
    "RelativeStrengthSignal",
    "SectorIdentifier",
    "SectorPerformance",
    "SectorRotationClassification",
    "SectorRotationSignal",
    "SectorRotationSnapshot",
]

