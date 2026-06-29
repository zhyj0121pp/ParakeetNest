"""Portfolio service boundary.

External brokerage API calls are intentionally not implemented yet.
"""


class PortfolioService:
    """Collect portfolio holdings, cash, cost basis, and unrealized P/L."""

    def fetch_holdings(self) -> tuple[dict[str, object], ...]:
        """Return placeholder holdings until brokerage integration exists."""
        return ()
