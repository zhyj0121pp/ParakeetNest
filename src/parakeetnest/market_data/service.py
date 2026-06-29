"""Provider-agnostic market data service orchestration."""

from __future__ import annotations

from parakeetnest.market_data.models import (
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    Symbol,
)
from parakeetnest.market_data.provider import MarketDataProvider, ProviderError


class MarketDataService:
    """Single entry point for provider-backed market data requests."""

    def __init__(self, provider: MarketDataProvider) -> None:
        """Initialize the service with one market data provider."""
        self._provider = provider

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Return a provider-backed snapshot for the symbol."""
        self._raise_if_unsupported(symbol)
        return self._provider.get_snapshot(symbol)

    def get_price_history(
        self,
        symbol: Symbol,
        data_range: MarketDataRange,
    ) -> list[PriceBar]:
        """Return provider-backed historical price bars for the symbol."""
        self._raise_if_unsupported(symbol)
        return self._provider.get_price_history(symbol, data_range)

    def _raise_if_unsupported(self, symbol: Symbol) -> None:
        if not self._provider.supports(symbol):
            raise ProviderError(f"Unsupported symbol: {symbol.ticker}")


__all__ = ["MarketDataService"]
