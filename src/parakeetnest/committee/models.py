"""Typed models for deterministic committee workflows."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from parakeetnest.context.models import MeetingContext as ResearchMeetingContext
from parakeetnest.models import (
    ConfidenceLevel,
    EvidenceItem,
    InvestmentHorizon,
    RecommendationAction,
)


class MeetingStatus(StrEnum):
    """Persistent lifecycle states for an AI committee meeting."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class MeetingRequest:
    """User request for a committee meeting."""

    question: str
    ticker: str


@dataclass(frozen=True)
class AgentResult:
    """Persistable output from one committee agent."""

    agent_name: str
    role: str
    content: str


@dataclass(frozen=True)
class MeetingContext:
    """Context passed through an AI committee meeting."""

    meeting_id: int
    question: str
    ticker: str
    research_context: ResearchMeetingContext
    rendered_investment_intelligence_context: str | None = None
    previous_agent_results: tuple[AgentResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MeetingResult:
    """Final persistable result for a committee meeting."""

    meeting_id: int
    status: MeetingStatus
    question: str
    ticker: str
    agent_results: tuple[AgentResult, ...] = field(default_factory=tuple)
    result_json: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class InvestmentContext:
    """Memory-first context provided to the committee before reasoning."""

    symbol: str
    historical_thesis: tuple[str, ...] = field(default_factory=tuple)
    historical_discussions: tuple[str, ...] = field(default_factory=tuple)
    current_facts: tuple[str, ...] = field(default_factory=tuple)
    data_quality_notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CommitteeOpinion:
    """A deterministic role-specific opinion from a committee member."""

    member_name: str
    role: str
    symbol: str
    viewpoint: str
    confidence: ConfidenceLevel
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    catalysts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ChairmanSummary:
    """Typed Chairman output after reviewing committee opinions."""

    symbol: str
    action: RecommendationAction
    confidence: ConfidenceLevel
    horizon: InvestmentHorizon
    rationale: str
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    catalysts: tuple[str, ...] = field(default_factory=tuple)
    data_confidence: ConfidenceLevel = ConfidenceLevel.LOW


@dataclass(frozen=True)
class CommitteeMeetingResult:
    """Complete typed output from one committee meeting."""

    context: InvestmentContext
    opinions: tuple[CommitteeOpinion, ...]
    chairman_summary: ChairmanSummary
    recorded: bool

    def __iter__(self) -> Iterator[object]:
        """Allow legacy tuple unpacking as opinions and chairman summary."""
        yield self.opinions
        yield self.chairman_summary
