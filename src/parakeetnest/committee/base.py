"""Base protocols for committee members."""

from __future__ import annotations

from typing import Protocol

from parakeetnest.committee.models import (
    AgentResult,
    CommitteeOpinion,
    InvestmentContext,
    MeetingContext,
)


class CommitteeMember(Protocol):
    """Protocol for deterministic committee participants."""

    name: str
    title: str

    def review(self, context: InvestmentContext) -> CommitteeOpinion:
        """Return this member's opinion for an investment context."""


class CommitteeAgent(Protocol):
    """Protocol for LLM-backed committee meeting agents."""

    name: str
    role: str

    def run(self, context: MeetingContext) -> AgentResult:
        """Return this agent's meeting result."""
