"""Market data service boundary.

External market data API calls are intentionally not implemented yet.
"""


class MarketDataService:
    """Collect price, volume, valuation, and range data for symbols."""

    def fetch_quote(self, symbol: str) -> dict[str, object]:
        """Return a placeholder quote for a symbol."""
        return {"symbol": symbol}
