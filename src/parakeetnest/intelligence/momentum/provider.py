"""Provider abstractions for Momentum Layer intelligence.

Providers own data access and normalization only. They return raw
provider-neutral inputs that the deterministic calculator can score without
knowing where the data came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class MomentumInputs:
    """Raw normalized momentum facts for a single symbol and date."""

    symbol: str
    as_of: date
    price_change_1m: float
    price_change_3m: float
    price_change_6m: float
    relative_strength: float
    trend_strength: float

    def __post_init__(self) -> None:
        """Normalize raw inputs without scoring or classification."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "price_change_1m", float(self.price_change_1m))
        object.__setattr__(self, "price_change_3m", float(self.price_change_3m))
        object.__setattr__(self, "price_change_6m", float(self.price_change_6m))
        object.__setattr__(self, "relative_strength", float(self.relative_strength))
        object.__setattr__(self, "trend_strength", float(self.trend_strength))


class MomentumProvider(Protocol):
    """Provider-neutral contract for retrieving raw momentum inputs."""

    def get_momentum_inputs(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumInputs:
        """Return raw momentum inputs for a symbol and optional date."""


__all__ = ["MomentumInputs", "MomentumProvider"]
