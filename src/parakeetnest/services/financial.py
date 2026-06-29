"""Financial service boundary.

External financial data API calls are intentionally not implemented yet.
"""


class FinancialService:
    """Collect revenue, EPS, margins, cash flow, and balance sheet data."""

    def fetch_financials(self, symbol: str) -> dict[str, object]:
        """Return placeholder financial data for a symbol."""
        return {"symbol": symbol}
