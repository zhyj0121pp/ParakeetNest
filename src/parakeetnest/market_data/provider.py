"""Provider contract for market data integrations."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

from parakeetnest.market_data.models import (
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    Symbol,
)
from parakeetnest.market_data.errors import MarketDataError


class ProviderCapability(str, Enum):
    """Provider-agnostic capabilities a market data source may support."""

    SNAPSHOT = "snapshot"
    PRICE_HISTORY = "price_history"


ProviderError = MarketDataError


@runtime_checkable
class MarketDataProvider(Protocol):
    """Small contract that all market data providers must implement."""

    def supports(self, symbol: Symbol) -> bool:
        """Return whether this provider can serve data for the symbol."""
        ...

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Return current point-in-time market data for the symbol."""
        ...

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        """Return historical price bars for the symbol and requested range."""
        ...


__all__ = [
    "MarketDataProvider",
    "ProviderCapability",
    "ProviderError",
]
