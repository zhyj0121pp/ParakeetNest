"""Yoyo, Chief Risk Officer."""

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.models import CommitteeMemo


class Yoyo(CommitteeMember):
    """Identify valuation, concentration, liquidity, earnings, and macro risks."""

    name = "Yoyo"
    title = "Chief Risk Officer"

    def review(self, symbol: str) -> CommitteeMemo:
        """Create a placeholder risk review."""
        return CommitteeMemo(
            role=self.title,
            symbol=symbol,
            summary="Risk review is pending validated portfolio and market data.",
        )
