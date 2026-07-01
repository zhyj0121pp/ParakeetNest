"""In-memory committee memory repository implementation.

This repository is intended for tests, local development, and early integration
work before durable storage is introduced.
"""

from __future__ import annotations

from parakeetnest.committee.memory.models import (
    CommitteeMemory,
    MemoryQuery,
    MemorySearchResult,
)
from parakeetnest.committee.memory.repository import (
    CommitteeMemoryRepository,
    validate_memory_id,
    validate_positive_limit,
)


class InMemoryCommitteeMemoryRepository(CommitteeMemoryRepository):
    """Concrete in-memory repository for committee memory records."""

    def __init__(self) -> None:
        self._memories: dict[str, CommitteeMemory] = {}

    def save(self, memory: CommitteeMemory) -> CommitteeMemory:
        """Persist a committee memory in process and return it."""
        memory_id = validate_memory_id(memory.memory_id)
        self._memories[memory_id] = memory
        return memory

    def get(self, memory_id: str) -> CommitteeMemory | None:
        """Return one committee memory by identifier, if present."""
        return self._memories.get(validate_memory_id(memory_id))

    def search(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        """Return deterministically ranked memories matching exact filters."""
        limit = validate_positive_limit(query.limit)
        matches = [
            memory
            for memory in self._memories.values()
            if _matches_query(memory=memory, query=query)
        ]
        ranked = sorted(
            matches,
            key=lambda memory: (memory.importance, memory.created_at, memory.memory_id),
            reverse=True,
        )
        return tuple(
            MemorySearchResult(memory=memory, relevance_score=1.0)
            for memory in ranked[:limit]
        )

    def delete(self, memory_id: str) -> bool:
        """Delete one committee memory by identifier."""
        normalized = validate_memory_id(memory_id)
        return self._memories.pop(normalized, None) is not None

    def list_recent(self, limit: int = 20) -> tuple[CommitteeMemory, ...]:
        """Return most recently created committee memories."""
        validate_positive_limit(limit)
        ranked = sorted(
            self._memories.values(),
            key=lambda memory: (memory.created_at, memory.memory_id),
            reverse=True,
        )
        return tuple(ranked[:limit])


def _matches_query(memory: CommitteeMemory, query: MemoryQuery) -> bool:
    if query.scope is not None and memory.scope is not query.scope:
        return False
    if query.memory_type is not None and memory.memory_type is not query.memory_type:
        return False
    if (
        query.importance_at_least is not None
        and memory.importance < query.importance_at_least
    ):
        return False
    if query.meeting_id is not None and memory.meeting_id != query.meeting_id:
        return False
    if query.agent_id is not None and memory.agent_id != query.agent_id:
        return False
    if query.ticker is not None and memory.ticker != query.ticker:
        return False
    if query.topic is not None and memory.topic != query.topic:
        return False
    return all(tag in memory.tags for tag in query.tags)
