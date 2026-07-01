"""Provider-neutral Market Sentiment Layer domain models.

The models in this module represent deterministic market sentiment derived
from structured market indicators. They avoid provider payloads, news text,
social-media inputs, LLM opinions, recommendation actions, and trading behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class SentimentRegime(str, Enum):
    """Provider-independent fear/greed regimes from normalized sentiment scores."""

    EXTREME_FEAR = "extreme_fear"
    FEAR = "fear"
    NEUTRAL = "neutral"
    GREED = "greed"
    EXTREME_GREED = "extreme_greed"


@dataclass(frozen=True)
class SentimentSignal:
    """One structured market sentiment signal used in the aggregate score."""

    name: str
    value: float
    normalized_score: float
    weight: float
    description: str | None = None

    def __post_init__(self) -> None:
        """Normalize signal fields without adding provider-specific behavior."""
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "value", float(self.value))
        object.__setattr__(self, "normalized_score", float(self.normalized_score))
        object.__setattr__(self, "weight", float(self.weight))
        if self.description is not None:
            description = self.description.strip()
            object.__setattr__(self, "description", description or None)


@dataclass(frozen=True)
class MarketSentimentSnapshot:
    """Point-in-time provider-neutral market sentiment assessment."""

    as_of: date
    overall_score: float
    confidence: float
    regime: SentimentRegime
    signals: tuple[SentimentSignal, ...] = field(default_factory=tuple)
    summary: str | None = None

    def __post_init__(self) -> None:
        """Normalize snapshot values without coupling to a data provider."""
        object.__setattr__(self, "overall_score", float(self.overall_score))
        object.__setattr__(self, "confidence", float(self.confidence))
        if not isinstance(self.regime, SentimentRegime):
            object.__setattr__(self, "regime", SentimentRegime(self.regime))
        object.__setattr__(
            self,
            "signals",
            tuple(self.signals),
        )
        if self.summary is not None:
            summary = self.summary.strip()
            object.__setattr__(self, "summary", summary or None)


__all__ = [
    "MarketSentimentSnapshot",
    "SentimentRegime",
    "SentimentSignal",
]
