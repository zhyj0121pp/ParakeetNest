"""Base protocols for committee members."""

from __future__ import annotations

from typing import Protocol

from parakeetnest.committee.models import CommitteeOpinion, InvestmentContext


class CommitteeMember(Protocol):
    """Protocol for deterministic committee participants."""

    name: str
    title: str

    def review(self, context: InvestmentContext) -> CommitteeOpinion:
        """Return this member's opinion for an investment context."""
