"""News service boundary.

External news API calls are intentionally not implemented yet.
"""


class NewsService:
    """Collect company, industry, AI, and semiconductor news."""

    def fetch_news(self, symbol: str) -> tuple[dict[str, object], ...]:
        """Return placeholder news items for a symbol."""
        return ()
