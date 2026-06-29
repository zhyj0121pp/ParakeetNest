"""Macro service boundary.

External macro data API calls are intentionally not implemented yet.
"""


class MacroService:
    """Collect rates, inflation, employment, and liquidity indicators."""

    def fetch_indicators(self) -> dict[str, object]:
        """Return placeholder macro indicators."""
        return {}
