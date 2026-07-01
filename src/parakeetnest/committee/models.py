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


class InvestmentCommitteeDecision(StrEnum):
    """Supported decisions for the complete investment committee product."""

    BUY = "buy"
    HOLD = "hold"
    WATCH = "watch"
    AVOID = "avoid"


@dataclass(frozen=True)
class MeetingRequest:
    """User request for a committee meeting."""

    question: str
    ticker: str


@dataclass(frozen=True)
class InvestmentCommitteeRequest:
    """Request for a complete investment committee review."""

    ticker: str
    topic: str
    time_horizon: InvestmentHorizon | str
    user_question: str | None = None
    portfolio_context_notes: str | None = None

    def __post_init__(self) -> None:
        """Normalize stable request fields without reaching into services."""
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        object.__setattr__(self, "topic", self.topic.strip())
        if isinstance(self.time_horizon, str):
            object.__setattr__(
                self,
                "time_horizon",
                InvestmentHorizon(self.time_horizon.strip()),
            )
        if self.user_question is not None:
            object.__setattr__(self, "user_question", self.user_question.strip())
        if self.portfolio_context_notes is not None:
            object.__setattr__(
                self,
                "portfolio_context_notes",
                self.portfolio_context_notes.strip(),
            )


@dataclass(frozen=True)
class InvestmentCommitteeReport:
    """Structured output for a complete investment committee review."""

    ticker: str
    topic: str
    time_horizon: InvestmentHorizon | str
    macro_view: str
    sector_view: str
    fundamental_view: str
    valuation_view: str
    risk_view: str
    momentum_sentiment_view: str
    bull_case: str
    bear_case: str
    key_risks: tuple[str, ...]
    decision: InvestmentCommitteeDecision | str
    confidence: ConfidenceLevel | str
    recommended_action: str

    def __post_init__(self) -> None:
        """Normalize enum-backed report fields."""
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        object.__setattr__(self, "topic", self.topic.strip())
        if isinstance(self.time_horizon, str):
            object.__setattr__(
                self,
                "time_horizon",
                InvestmentHorizon(self.time_horizon.strip()),
            )
        if isinstance(self.decision, str):
            object.__setattr__(
                self,
                "decision",
                InvestmentCommitteeDecision(self.decision.strip().lower()),
            )
        if isinstance(self.confidence, str):
            object.__setattr__(
                self,
                "confidence",
                ConfidenceLevel(self.confidence.strip().lower()),
            )
        object.__setattr__(self, "key_risks", tuple(self.key_risks))


@dataclass(frozen=True)
class InvestmentCommitteeMember:
    """Role metadata for the default complete investment committee."""

    name: str
    role: str


DEFAULT_INVESTMENT_COMMITTEE: tuple[InvestmentCommitteeMember, ...] = (
    InvestmentCommitteeMember(
        name="Macro Strategist",
        role="Assesses economic regime, rates, inflation, and liquidity backdrop.",
    ),
    InvestmentCommitteeMember(
        name="Sector Analyst",
        role="Assesses sector structure, rotation, industry trends, and peers.",
    ),
    InvestmentCommitteeMember(
        name="Fundamental Analyst",
        role="Assesses business quality, growth, margins, and financial durability.",
    ),
    InvestmentCommitteeMember(
        name="Valuation Analyst",
        role="Assesses valuation, assumptions, upside, and downside scenarios.",
    ),
    InvestmentCommitteeMember(
        name="Risk Manager",
        role="Assesses downside risks, position sizing concerns, and red flags.",
    ),
    InvestmentCommitteeMember(
        name="Momentum / Sentiment Analyst",
        role="Assesses price momentum, market sentiment, and positioning.",
    ),
    InvestmentCommitteeMember(
        name="Chair / CIO",
        role="Synthesizes views into a final decision and recommended action.",
    ),
)


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
    investment_committee_request: InvestmentCommitteeRequest | None = None
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
