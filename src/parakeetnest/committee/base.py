"""Base abstractions for committee members."""

from __future__ import annotations

from abc import ABC, abstractmethod

from parakeetnest.models import CommitteeMemo


class CommitteeMember(ABC):
    """Base class for committee participants."""

    name: str
    title: str

    @abstractmethod
    def review(self, symbol: str) -> CommitteeMemo:
        """Return this member's initial review for a symbol."""
