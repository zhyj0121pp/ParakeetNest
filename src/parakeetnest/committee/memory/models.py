"""Domain models for committee memory.

These models describe durable committee memory records and query envelopes.
They do not persist memory, retrieve memory, build embeddings, render prompts,
or integrate with committee runtime execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class MemoryScope(StrEnum):
    """Scope where a committee memory is relevant."""

    COMMITTEE = "committee"
    AGENT = "agent"
    PORTFOLIO = "portfolio"
    WATCHLIST = "watchlist"


class MemoryType(StrEnum):
    """Stable committee memory category identifiers."""

    MEETING_SUMMARY = "meeting_summary"
    AGENT_OBSERVATION = "agent_observation"
    INVESTMENT_THESIS = "investment_thesis"
    RISK_FLAG = "risk_flag"
    ACTION_ITEM = "action_item"
    DECISION = "decision"
    FOLLOW_UP = "follow_up"


class MemoryImportance(IntEnum):
    """Relative priority for selecting and surfacing memories."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class CommitteeMemory:
    """One immutable memory item produced by or for the committee."""

    memory_id: str
    scope: MemoryScope
    memory_type: MemoryType
    importance: MemoryImportance
    content: str
    created_at: datetime
    updated_at: datetime | None = None
    meeting_id: str | None = None
    agent_id: str | None = None
    ticker: str | None = None
    topic: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        memory_id = self.memory_id.strip()
        content = self.content.strip()

        if not memory_id:
            raise ValueError("memory_id is required")
        if not content:
            raise ValueError("content is required")

        object.__setattr__(self, "memory_id", memory_id)
        object.__setattr__(self, "scope", MemoryScope(self.scope))
        object.__setattr__(self, "memory_type", MemoryType(self.memory_type))
        object.__setattr__(self, "importance", MemoryImportance(self.importance))
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "meeting_id", _normalize_optional(self.meeting_id))
        object.__setattr__(self, "agent_id", _normalize_optional(self.agent_id))
        object.__setattr__(self, "ticker", _normalize_optional_upper(self.ticker))
        object.__setattr__(self, "topic", _normalize_optional(self.topic))
        object.__setattr__(self, "tags", _normalize_strings(self.tags, "tags"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def is_agent_memory(self) -> bool:
        """Return whether this memory is scoped to a specific agent."""
        return self.scope is MemoryScope.AGENT

    def is_committee_memory(self) -> bool:
        """Return whether this memory is scoped to the full committee."""
        return self.scope is MemoryScope.COMMITTEE

    def is_high_importance(self) -> bool:
        """Return whether this memory is high priority or critical."""
        return self.importance >= MemoryImportance.HIGH

    def with_updated_content(self, content: str) -> CommitteeMemory:
        """Return a copy with updated content and updated_at set to now."""
        return replace(self, content=content, updated_at=datetime.now(self.created_at.tzinfo))


@dataclass(frozen=True)
class MemoryQuery:
    """Optional filters for selecting committee memories."""

    scope: MemoryScope | None = None
    memory_type: MemoryType | None = None
    importance_at_least: MemoryImportance | None = None
    meeting_id: str | None = None
    agent_id: str | None = None
    ticker: str | None = None
    topic: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    limit: int = 20

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be positive")

        object.__setattr__(
            self,
            "scope",
            None if self.scope is None else MemoryScope(self.scope),
        )
        object.__setattr__(
            self,
            "memory_type",
            None if self.memory_type is None else MemoryType(self.memory_type),
        )
        object.__setattr__(
            self,
            "importance_at_least",
            None
            if self.importance_at_least is None
            else MemoryImportance(self.importance_at_least),
        )
        object.__setattr__(self, "meeting_id", _normalize_optional(self.meeting_id))
        object.__setattr__(self, "agent_id", _normalize_optional(self.agent_id))
        object.__setattr__(self, "ticker", _normalize_optional_upper(self.ticker))
        object.__setattr__(self, "topic", _normalize_optional(self.topic))
        object.__setattr__(self, "tags", _normalize_strings(self.tags, "tags"))


@dataclass(frozen=True)
class MemorySearchResult:
    """One scored memory result returned by a future retrieval engine."""

    memory: CommitteeMemory
    relevance_score: float
    reason: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        object.__setattr__(self, "reason", _normalize_optional(self.reason))


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("optional string fields cannot be blank")
    return normalized


def _normalize_optional_upper(value: str | None) -> str | None:
    normalized = _normalize_optional(value)
    return None if normalized is None else normalized.upper()


def _normalize_strings(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item:
            raise ValueError(f"{field_name} cannot contain blank values")
        normalized.append(item)
    return tuple(normalized)


def _freeze_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))
