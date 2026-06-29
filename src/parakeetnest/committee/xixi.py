"""Xixi, Chief Fundamental Analyst."""

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.models import CommitteeMemo


class Xixi(CommitteeMember):
    """Evaluate business quality, durability, and long-term fundamentals."""

    name = "Xixi"
    title = "Chief Fundamental Analyst"

    def review(self, symbol: str) -> CommitteeMemo:
        """Create a placeholder fundamental review."""
        return CommitteeMemo(
            role=self.title,
            symbol=symbol,
            summary="Fundamental review is pending validated company data.",
        )
