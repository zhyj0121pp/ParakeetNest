"""Provider-neutral Watchlist Intelligence domain models.

The models in this module represent committee-ready watchlist research shapes.
They avoid provider payloads, persistence, LLM calls, CLI behavior, and trading
execution so later watchlist services can compose them safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class WatchlistPriority(str, Enum):
    """Provider-neutral priority for watchlist attention."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WatchlistStatus(str, Enum):
    """Lifecycle status for a watchlist item."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class WatchlistItem:
    """One investment candidate tracked by the committee."""

    symbol: str
    company_name: str | None = None
    sector: str | None = None
    theme: str | None = None
    reason: str | None = None
    priority: WatchlistPriority = WatchlistPriority.MEDIUM
    status: WatchlistStatus = WatchlistStatus.ACTIVE
    notes: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize stable watchlist identity and metadata."""
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol))
        object.__setattr__(
            self,
            "company_name",
            _normalize_optional(self.company_name),
        )
        object.__setattr__(self, "sector", _normalize_optional(self.sector))
        object.__setattr__(self, "theme", _normalize_optional(self.theme))
        object.__setattr__(self, "reason", _normalize_optional(self.reason))
        if not isinstance(self.priority, WatchlistPriority):
            object.__setattr__(self, "priority", WatchlistPriority(self.priority))
        if not isinstance(self.status, WatchlistStatus):
            object.__setattr__(self, "status", WatchlistStatus(self.status))
        object.__setattr__(self, "notes", _normalize_strings(self.notes))
        object.__setattr__(
            self,
            "updated_at",
            self.created_at if self.updated_at is None else self.updated_at,
        )


@dataclass(frozen=True)
class WatchlistThesis:
    """Investment thesis for a watchlist symbol."""

    symbol: str
    thesis: str
    key_drivers: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    time_horizon: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        """Normalize thesis text and supporting lists."""
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol))
        object.__setattr__(self, "thesis", _normalize_required(self.thesis, "thesis"))
        object.__setattr__(self, "key_drivers", _normalize_strings(self.key_drivers))
        object.__setattr__(self, "risks", _normalize_strings(self.risks))
        object.__setattr__(
            self,
            "time_horizon",
            _normalize_optional(self.time_horizon),
        )
        if self.confidence is not None:
            object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True)
class WatchlistSignal:
    """Provider-neutral signal that may change watchlist attention."""

    symbol: str
    signal_type: str
    summary: str
    strength: float
    source: str | None = None

    def __post_init__(self) -> None:
        """Normalize a single watchlist signal."""
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol))
        object.__setattr__(
            self,
            "signal_type",
            _normalize_required(self.signal_type, "signal_type").lower(),
        )
        object.__setattr__(self, "summary", _normalize_required(self.summary, "summary"))
        object.__setattr__(self, "strength", float(self.strength))
        object.__setattr__(self, "source", _normalize_optional(self.source))


@dataclass(frozen=True)
class WatchlistInsight:
    """Committee-ready watchlist synthesis for one symbol."""

    symbol: str
    summary: str
    bullish_factors: tuple[str, ...] = field(default_factory=tuple)
    bearish_factors: tuple[str, ...] = field(default_factory=tuple)
    open_questions: tuple[str, ...] = field(default_factory=tuple)
    recommended_action: str | None = None

    def __post_init__(self) -> None:
        """Normalize watchlist insight text and factors."""
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol))
        object.__setattr__(self, "summary", _normalize_required(self.summary, "summary"))
        object.__setattr__(
            self,
            "bullish_factors",
            _normalize_strings(self.bullish_factors),
        )
        object.__setattr__(
            self,
            "bearish_factors",
            _normalize_strings(self.bearish_factors),
        )
        object.__setattr__(
            self,
            "open_questions",
            _normalize_strings(self.open_questions),
        )
        object.__setattr__(
            self,
            "recommended_action",
            _normalize_optional(self.recommended_action),
        )


def _normalize_symbol(value: str) -> str:
    """Return an uppercase investment symbol."""
    symbol = str(value).strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    return symbol


def _normalize_required(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_strings(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


__all__ = [
    "WatchlistInsight",
    "WatchlistItem",
    "WatchlistPriority",
    "WatchlistSignal",
    "WatchlistStatus",
    "WatchlistThesis",
]
