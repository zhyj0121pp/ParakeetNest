"""Provider-neutral Momentum Layer domain models.

The models in this module are immutable research snapshots. They intentionally
avoid provider payloads, API credentials, persistence concerns, recommendation
actions, and trading behavior so the Momentum Layer can be reused with any data
adapter that satisfies the provider contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class MomentumRegime(str, Enum):
    """Provider-independent momentum regimes derived from normalized scores."""

    STRONG_UPTREND = "strong_uptrend"
    UPTREND = "uptrend"
    NEUTRAL = "neutral"
    DOWNTREND = "downtrend"
    STRONG_DOWNTREND = "strong_downtrend"


class ReversalRisk(str, Enum):
    """Provider-neutral risk levels for short-term momentum reversals."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class MomentumSnapshot:
    """Point-in-time momentum assessment for one investment symbol.

    Raw price-change, relative-strength, and trend-strength fields are preserved
    beside calculator-owned outputs so callers can inspect both the evidence and
    the deterministic classification without depending on a concrete provider.
    """

    symbol: str
    as_of: date
    price_change_1m: float
    price_change_3m: float
    price_change_6m: float
    relative_strength: float
    trend_strength: float
    momentum_score: float
    momentum_regime: MomentumRegime
    reversal_risk: ReversalRisk
    confidence: float
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize snapshot values without coupling to a data provider."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "price_change_1m", float(self.price_change_1m))
        object.__setattr__(self, "price_change_3m", float(self.price_change_3m))
        object.__setattr__(self, "price_change_6m", float(self.price_change_6m))
        object.__setattr__(self, "relative_strength", float(self.relative_strength))
        object.__setattr__(self, "trend_strength", float(self.trend_strength))
        object.__setattr__(self, "momentum_score", float(self.momentum_score))
        if not isinstance(self.momentum_regime, MomentumRegime):
            object.__setattr__(
                self,
                "momentum_regime",
                MomentumRegime(self.momentum_regime),
            )
        if not isinstance(self.reversal_risk, ReversalRisk):
            object.__setattr__(
                self,
                "reversal_risk",
                ReversalRisk(self.reversal_risk),
            )
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(
            self,
            "evidence",
            tuple(item.strip() for item in self.evidence if item.strip()),
        )


__all__ = ["MomentumRegime", "MomentumSnapshot", "ReversalRisk"]
