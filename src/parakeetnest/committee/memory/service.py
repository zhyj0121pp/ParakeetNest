"""Application service for committee memory operations.

The service coordinates creation of committee memory domain objects and
delegates persistence and retrieval to a repository implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import uuid4

from parakeetnest.committee.memory.models import (
    CommitteeMemory,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)
from parakeetnest.committee.memory.repository import CommitteeMemoryRepository


class CommitteeMemoryService:
    """Application boundary between committee runtime and memory repository."""

    def __init__(self, repository: CommitteeMemoryRepository) -> None:
        """Initialize the service with an explicit memory repository."""
        self._repository = repository

    def save_memory(self, memory: CommitteeMemory) -> CommitteeMemory:
        """Persist an existing committee memory through the repository."""
        return self._repository.save(memory)

    def get_memory(self, memory_id: str) -> CommitteeMemory | None:
        """Return one committee memory by identifier, if present."""
        return self._repository.get(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        """Delete one committee memory by identifier."""
        return self._repository.delete(memory_id)

    def list_recent(self, limit: int = 20) -> tuple[CommitteeMemory, ...]:
        """Return recently saved committee memories."""
        return self._repository.list_recent(limit=limit)

    def search(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        """Return repository-backed committee memory search results."""
        return self._repository.search(query)

    def save_meeting_summary(
        self,
        meeting_id: str,
        content: str,
        importance: MemoryImportance = MemoryImportance.HIGH,
        metadata: Mapping[str, Any] | None = None,
    ) -> CommitteeMemory:
        """Create and save a committee-scoped meeting summary memory."""
        return self.save_memory(
            CommitteeMemory(
                memory_id=_new_memory_id(),
                scope=MemoryScope.COMMITTEE,
                memory_type=MemoryType.MEETING_SUMMARY,
                importance=importance,
                content=content,
                created_at=_now_utc(),
                meeting_id=meeting_id,
                metadata={} if metadata is None else metadata,
            )
        )

    def save_agent_observation(
        self,
        meeting_id: str,
        agent_id: str,
        ticker: str | None,
        content: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        metadata: Mapping[str, Any] | None = None,
    ) -> CommitteeMemory:
        """Create and save an agent-scoped observation memory."""
        return self.save_memory(
            CommitteeMemory(
                memory_id=_new_memory_id(),
                scope=MemoryScope.AGENT,
                memory_type=MemoryType.AGENT_OBSERVATION,
                importance=importance,
                content=content,
                created_at=_now_utc(),
                meeting_id=meeting_id,
                agent_id=agent_id,
                ticker=ticker,
                metadata={} if metadata is None else metadata,
            )
        )

    def save_decision(
        self,
        meeting_id: str,
        content: str,
        importance: MemoryImportance = MemoryImportance.CRITICAL,
    ) -> CommitteeMemory:
        """Create and save a committee-scoped decision memory."""
        return self.save_memory(
            CommitteeMemory(
                memory_id=_new_memory_id(),
                scope=MemoryScope.COMMITTEE,
                memory_type=MemoryType.DECISION,
                importance=importance,
                content=content,
                created_at=_now_utc(),
                meeting_id=meeting_id,
            )
        )


def _new_memory_id() -> str:
    return str(uuid4())


def _now_utc() -> datetime:
    return datetime.now(UTC)


__all__ = ["CommitteeMemoryService"]
