"""Tests for committee memory repository contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.committee.memory import (
    CommitteeMemory,
    CommitteeMemoryRepository,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
    validate_memory_id,
    validate_positive_limit,
)


class FakeCommitteeMemoryRepository(CommitteeMemoryRepository):
    """Small fake used only to verify the repository contract."""

    def __init__(self) -> None:
        self._memories: dict[str, CommitteeMemory] = {}

    def save(self, memory: CommitteeMemory) -> CommitteeMemory:
        self._memories[memory.memory_id] = memory
        return memory

    def get(self, memory_id: str) -> CommitteeMemory | None:
        return self._memories.get(validate_memory_id(memory_id))

    def search(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        matches = [
            memory
            for memory in self._memories.values()
            if _matches_query(memory=memory, query=query)
        ]
        return tuple(
            MemorySearchResult(memory=memory, relevance_score=1.0)
            for memory in matches[: query.limit]
        )

    def delete(self, memory_id: str) -> bool:
        normalized = validate_memory_id(memory_id)
        return self._memories.pop(normalized, None) is not None

    def list_recent(self, limit: int = 20) -> tuple[CommitteeMemory, ...]:
        validate_positive_limit(limit)
        memories = sorted(
            self._memories.values(),
            key=lambda memory: memory.created_at,
            reverse=True,
        )
        return tuple(memories[:limit])


def _memory(
    memory_id: str = "memory-1",
    *,
    ticker: str = "NVDA",
    created_at: datetime = datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
) -> CommitteeMemory:
    return CommitteeMemory(
        memory_id=memory_id,
        scope=MemoryScope.AGENT,
        memory_type=MemoryType.AGENT_OBSERVATION,
        importance=MemoryImportance.HIGH,
        content="Xixi noted durable margin expansion.",
        created_at=created_at,
        agent_id="xixi",
        ticker=ticker,
        tags=("margins",),
    )


def _matches_query(memory: CommitteeMemory, query: MemoryQuery) -> bool:
    if query.scope is not None and memory.scope is not query.scope:
        return False
    if query.memory_type is not None and memory.memory_type is not query.memory_type:
        return False
    if query.importance_at_least is not None and memory.importance < query.importance_at_least:
        return False
    if query.agent_id is not None and memory.agent_id != query.agent_id:
        return False
    if query.ticker is not None and memory.ticker != query.ticker:
        return False
    return all(tag in memory.tags for tag in query.tags)


def test_repository_interface_can_be_subclassed() -> None:
    repository: CommitteeMemoryRepository = FakeCommitteeMemoryRepository()

    saved = repository.save(_memory())

    assert repository.get("memory-1") == saved


def test_repository_fake_supports_required_methods() -> None:
    repository = FakeCommitteeMemoryRepository()
    older = _memory("memory-1", ticker="NVDA", created_at=datetime(2026, 7, 1, tzinfo=UTC))
    newer = _memory("memory-2", ticker="AAPL", created_at=datetime(2026, 7, 2, tzinfo=UTC))

    assert repository.save(older) == older
    assert repository.save(newer) == newer
    assert repository.get("memory-2") == newer

    results = repository.search(MemoryQuery(ticker="nvda"))

    assert results == (MemorySearchResult(memory=older, relevance_score=1.0),)
    assert repository.list_recent(limit=1) == (newer,)
    assert repository.delete("memory-1")
    assert repository.get("memory-1") is None
    assert not repository.delete("memory-1")


def test_validate_memory_id_rejects_blank_values() -> None:
    assert validate_memory_id(" memory-1 ") == "memory-1"

    with pytest.raises(ValueError, match="memory_id cannot be blank"):
        validate_memory_id(" ")


def test_validate_positive_limit_rejects_non_positive_values() -> None:
    assert validate_positive_limit(20) == 20

    with pytest.raises(ValueError, match="limit must be positive"):
        validate_positive_limit(0)

    with pytest.raises(ValueError, match="limit must be positive"):
        FakeCommitteeMemoryRepository().list_recent(limit=-1)
