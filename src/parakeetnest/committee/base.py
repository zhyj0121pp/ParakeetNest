"""Base protocols for committee members."""

from __future__ import annotations

from typing import Protocol

from parakeetnest.committee.models import (
    CommitteeOpinion,
    InvestmentContext,
)


class CommitteeMember(Protocol):
    """Protocol for deterministic committee participants."""

    name: str
    title: str

    def review(self, context: InvestmentContext) -> CommitteeOpinion:
        """Return this member's opinion for an investment context."""


class CommitteeAgent(Protocol):
    """Protocol for prompt-backed committee meeting agent definitions."""

    agent_id: str
    name: str
    role: str
    prompt_filename: str
