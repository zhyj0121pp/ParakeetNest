"""Shared domain models for ParakeetNest."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class RecommendationAction(StrEnum):
    """Supported investment recommendation actions."""

    BUY = "buy"
    HOLD = "hold"
    REDUCE = "reduce"
    WATCH = "watch"


class ConfidenceLevel(StrEnum):
    """Human-readable confidence levels for committee conclusions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InvestmentHorizon(StrEnum):
    """Supported investment horizons."""

    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    ONE_YEAR = "1_year"
    THREE_YEARS = "3_years"


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of supporting evidence with source attribution."""

    summary: str
    source: str
    observed_at: datetime | None = None


@dataclass(frozen=True)
class Recommendation:
    """A complete committee recommendation.

    Every recommendation includes action, confidence, horizon, evidence,
    risks, and catalysts as required by the project rules.
    """

    symbol: str
    action: RecommendationAction
    confidence: ConfidenceLevel
    horizon: InvestmentHorizon
    evidence: tuple[EvidenceItem, ...]
    risks: tuple[str, ...]
    catalysts: tuple[str, ...]
    data_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    created_at: datetime | None = None


@dataclass(frozen=True)
class CommitteeMemo:
    """A role-specific committee note produced during a meeting."""

    role: str
    symbol: str
    summary: str
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    catalysts: tuple[str, ...] = field(default_factory=tuple)
