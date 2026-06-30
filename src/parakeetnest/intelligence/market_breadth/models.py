"""Provider-neutral Market Breadth domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class BreadthRegime(str, Enum):
    """Provider-independent market breadth regimes."""

    STRONG = "strong"
    HEALTHY = "healthy"
    NEUTRAL = "neutral"
    WEAK = "weak"
    STRESSED = "stressed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MarketBreadthSnapshot:
    """Point-in-time provider-neutral market breadth snapshot."""

    universe: str
    date: date
    advancers: int
    decliners: int
    unchanged: int
    new_highs: int
    new_lows: int
    percent_above_20d_ma: float
    percent_above_50d_ma: float
    percent_above_200d_ma: float
    up_volume: float
    down_volume: float
    breadth_score: float
    breadth_regime: BreadthRegime
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize snapshot values without coupling to a data provider."""
        object.__setattr__(self, "universe", self.universe.strip().upper())
        object.__setattr__(self, "advancers", int(self.advancers))
        object.__setattr__(self, "decliners", int(self.decliners))
        object.__setattr__(self, "unchanged", int(self.unchanged))
        object.__setattr__(self, "new_highs", int(self.new_highs))
        object.__setattr__(self, "new_lows", int(self.new_lows))
        object.__setattr__(
            self,
            "percent_above_20d_ma",
            float(self.percent_above_20d_ma),
        )
        object.__setattr__(
            self,
            "percent_above_50d_ma",
            float(self.percent_above_50d_ma),
        )
        object.__setattr__(
            self,
            "percent_above_200d_ma",
            float(self.percent_above_200d_ma),
        )
        object.__setattr__(self, "up_volume", float(self.up_volume))
        object.__setattr__(self, "down_volume", float(self.down_volume))
        object.__setattr__(self, "breadth_score", float(self.breadth_score))
        if not isinstance(self.breadth_regime, BreadthRegime):
            object.__setattr__(
                self,
                "breadth_regime",
                BreadthRegime(self.breadth_regime),
            )
        object.__setattr__(
            self,
            "warnings",
            tuple(item.strip() for item in self.warnings if item.strip()),
        )


__all__ = ["BreadthRegime", "MarketBreadthSnapshot"]
