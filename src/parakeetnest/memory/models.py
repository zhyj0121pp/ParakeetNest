"""Domain models for the investment knowledge base."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class ThesisVersion:
    """One immutable version of an investment thesis."""

    symbol: str
    version: int
    thesis: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    catalysts: tuple[str, ...] = field(default_factory=tuple)
    invalidation_conditions: tuple[str, ...] = field(default_factory=tuple)
    author: str = "Investment Secretary"
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class InvestmentThesis:
    """Append-only investment thesis history for one symbol."""

    symbol: str
    versions: tuple[ThesisVersion, ...] = field(default_factory=tuple)

    @property
    def latest(self) -> ThesisVersion | None:
        """Return the latest thesis version."""
        return self.versions[-1] if self.versions else None


@dataclass(frozen=True)
class ResearchNote:
    """A research note attached to a company or broad topic."""

    title: str
    body: str
    symbol: str | None = None
    source: str = "manual"
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class LessonLearned:
    """A lesson learned from committee history or investment outcomes."""

    lesson: str
    symbol: str | None = None
    source: str = "manual"
    created_at: datetime = field(default_factory=utc_now)
