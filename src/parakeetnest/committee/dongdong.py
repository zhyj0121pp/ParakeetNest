"""Dongdong, Chief Opportunity Hunter."""

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.models import CommitteeMemo


class Dongdong(CommitteeMember):
    """Search for overlooked growth opportunities and catalysts."""

    name = "Dongdong"
    title = "Chief Opportunity Hunter"

    def review(self, symbol: str) -> CommitteeMemo:
        """Create a placeholder opportunity review."""
        return CommitteeMemo(
            role=self.title,
            symbol=symbol,
            summary="Opportunity review is pending validated market and catalyst data.",
        )
