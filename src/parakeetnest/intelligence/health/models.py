"""Provider-neutral Market Health Layer domain models.

The models in this module represent a deterministic composite assessment of
market health from existing investment intelligence layers. They avoid provider
payloads, external data access, recommendation actions, and trading behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class MarketHealthState(str, Enum):
    """Provider-independent market health states from normalized scores."""

    ROBUST = "robust"
    HEALTHY = "healthy"
    FRAGILE = "fragile"
    DETERIORATING = "deteriorating"
    STRESSED = "stressed"
    UNKNOWN = "unknown"


class HealthComponentState(str, Enum):
    """Provider-neutral state for one market health component."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MarketHealthComponent:
    """One provider-neutral component in the aggregate market health score."""

    name: str
    state: HealthComponentState
    score: float | None = None
    weight: float | None = None
    evidence: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize stable component fields without provider-specific behavior."""
        object.__setattr__(self, "name", self.name.strip().lower())
        if not isinstance(self.state, HealthComponentState):
            object.__setattr__(self, "state", HealthComponentState(self.state))
        if self.score is not None:
            object.__setattr__(self, "score", float(self.score))
        if self.weight is not None:
            object.__setattr__(self, "weight", float(self.weight))
        object.__setattr__(
            self,
            "evidence",
            tuple(item.strip() for item in self.evidence if item.strip()),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class MarketHealthSnapshot:
    """Point-in-time provider-neutral aggregate market health assessment."""

    as_of: date
    universe: str
    health_state: MarketHealthState
    health_score: float
    confidence: float
    components: tuple[MarketHealthComponent, ...] = field(default_factory=tuple)
    positives: tuple[str, ...] = field(default_factory=tuple)
    negatives: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize snapshot values without coupling to a data provider."""
        object.__setattr__(self, "universe", self.universe.strip().upper())
        if not isinstance(self.health_state, MarketHealthState):
            object.__setattr__(
                self,
                "health_state",
                MarketHealthState(self.health_state),
            )
        object.__setattr__(self, "health_score", float(self.health_score))
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(
            self,
            "positives",
            tuple(item.strip() for item in self.positives if item.strip()),
        )
        object.__setattr__(
            self,
            "negatives",
            tuple(item.strip() for item in self.negatives if item.strip()),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(item.strip() for item in self.warnings if item.strip()),
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


__all__ = [
    "HealthComponentState",
    "MarketHealthComponent",
    "MarketHealthSnapshot",
    "MarketHealthState",
]
