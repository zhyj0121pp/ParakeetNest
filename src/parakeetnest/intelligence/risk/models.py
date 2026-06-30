"""Provider-neutral Risk Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class RiskLevel(str, Enum):
    """Provider-independent risk severity levels."""

    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"


class RiskCategory(str, Enum):
    """Provider-neutral risk signal categories."""

    MARKET = "market"
    SECTOR = "sector"
    VALUATION = "valuation"
    MACRO = "macro"
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"
    DRAWDOWN = "drawdown"
    LIQUIDITY = "liquidity"


@dataclass(frozen=True)
class RiskSignal:
    """One provider-neutral risk signal with supporting evidence."""

    category: RiskCategory
    level: RiskLevel
    score: float
    label: str
    description: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize enums and stable text fields."""
        if not isinstance(self.category, RiskCategory):
            object.__setattr__(self, "category", RiskCategory(self.category))
        if not isinstance(self.level, RiskLevel):
            object.__setattr__(self, "level", RiskLevel(self.level))
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(
            self,
            "evidence",
            tuple(item.strip() for item in self.evidence if item.strip()),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class RiskAssessment:
    """Point-in-time provider-neutral aggregate risk assessment."""

    overall_level: RiskLevel
    overall_score: float
    signals: list[RiskSignal] = field(default_factory=list)
    as_of_date: date | None = None
    summary: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        """Normalize aggregate risk metadata without provider coupling."""
        if not isinstance(self.overall_level, RiskLevel):
            object.__setattr__(self, "overall_level", RiskLevel(self.overall_level))
        object.__setattr__(self, "overall_score", float(self.overall_score))
        object.__setattr__(
            self,
            "signals",
            sorted(
                self.signals,
                key=lambda signal: (
                    signal.category.value,
                    signal.level.value,
                    signal.label.lower(),
                ),
            ),
        )
        if self.summary is not None:
            object.__setattr__(self, "summary", self.summary.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


@dataclass(frozen=True)
class RiskSummary:
    """Compact risk summary for later committee context rendering."""

    overall_level: RiskLevel
    overall_score: float
    headline: str
    top_risks: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize compact summary fields."""
        if not isinstance(self.overall_level, RiskLevel):
            object.__setattr__(self, "overall_level", RiskLevel(self.overall_level))
        object.__setattr__(self, "overall_score", float(self.overall_score))
        object.__setattr__(self, "headline", self.headline.strip())
        object.__setattr__(
            self,
            "top_risks",
            tuple(item.strip() for item in self.top_risks if item.strip()),
        )
        object.__setattr__(
            self,
            "evidence",
            tuple(item.strip() for item in self.evidence if item.strip()),
        )


__all__ = [
    "RiskAssessment",
    "RiskCategory",
    "RiskLevel",
    "RiskSignal",
    "RiskSummary",
]
