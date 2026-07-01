"""Tests for the in-memory committee memory repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from parakeetnest.committee.memory import (
    CommitteeMemory,
    InMemoryCommitteeMemoryRepository,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)


def _memory(
    memory_id: str,
    *,
    created_at: datetime | None = None,
    scope: MemoryScope = MemoryScope.AGENT,
    memory_type: MemoryType = MemoryType.AGENT_OBSERVATION,
    importance: MemoryImportance = MemoryImportance.MEDIUM,
    meeting_id: str | None = "meeting-1",
    agent_id: str | None = "xixi",
    ticker: str | None = "NVDA",
    topic: str | None = "AI infrastructure margins",
    tags: tuple[str, ...] = ("margins",),
) -> CommitteeMemory:
    return CommitteeMemory(
        memory_id=memory_id,
        scope=scope,
        memory_type=memory_type,
        importance=importance,
        content=f"Committee memory {memory_id}.",
        created_at=created_at or datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        meeting_id=meeting_id,
        agent_id=agent_id,
        ticker=ticker,
        topic=topic,
        tags=tags,
    )


def test_save_and_get() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    memory = _memory("memory-1")

    saved = repository.save(memory)

    assert saved == memory
    assert repository.get("memory-1") == memory


def test_save_overwrites_same_memory_id() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    original = _memory("memory-1", importance=MemoryImportance.LOW)
    replacement = _memory("memory-1", importance=MemoryImportance.CRITICAL)

    repository.save(original)
    repository.save(replacement)

    assert repository.get("memory-1") == replacement
    assert repository.list_recent() == (replacement,)


def test_delete_existing_and_missing_memory() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    memory = _memory("memory-1")
    repository.save(memory)

    assert repository.delete("memory-1")
    assert repository.get("memory-1") is None
    assert not repository.delete("memory-1")


def test_list_recent_orders_by_created_at_and_respects_limit() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    base_time = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    oldest = _memory("memory-1", created_at=base_time)
    newest = _memory("memory-2", created_at=base_time + timedelta(minutes=2))
    middle = _memory("memory-3", created_at=base_time + timedelta(minutes=1))

    repository.save(oldest)
    repository.save(newest)
    repository.save(middle)

    assert repository.list_recent(limit=2) == (newest, middle)


def test_search_by_ticker() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    nvda = _memory("memory-1", ticker="NVDA")
    aapl = _memory("memory-2", ticker="AAPL")
    repository.save(nvda)
    repository.save(aapl)

    results = repository.search(MemoryQuery(ticker="nvda"))

    assert results == (MemorySearchResult(memory=nvda, relevance_score=1.0),)


def test_search_by_agent_id() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    xixi = _memory("memory-1", agent_id="xixi")
    yoyo = _memory("memory-2", agent_id="yoyo")
    repository.save(xixi)
    repository.save(yoyo)

    results = repository.search(MemoryQuery(agent_id="yoyo"))

    assert results == (MemorySearchResult(memory=yoyo, relevance_score=1.0),)


def test_search_by_importance_at_least() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    low = _memory("memory-1", importance=MemoryImportance.LOW)
    high = _memory("memory-2", importance=MemoryImportance.HIGH)
    critical = _memory("memory-3", importance=MemoryImportance.CRITICAL)
    repository.save(low)
    repository.save(high)
    repository.save(critical)

    results = repository.search(MemoryQuery(importance_at_least=MemoryImportance.HIGH))

    assert results == (
        MemorySearchResult(memory=critical, relevance_score=1.0),
        MemorySearchResult(memory=high, relevance_score=1.0),
    )


def test_search_by_tags() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    matching = _memory("memory-1", tags=("margins", "earnings", "watchlist"))
    partial = _memory("memory-2", tags=("margins",))
    repository.save(matching)
    repository.save(partial)

    results = repository.search(MemoryQuery(tags=("margins", "earnings")))

    assert results == (MemorySearchResult(memory=matching, relevance_score=1.0),)


def test_search_respects_limit() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    base_time = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    low_new = _memory(
        "memory-1",
        created_at=base_time + timedelta(minutes=3),
        importance=MemoryImportance.LOW,
    )
    high_old = _memory(
        "memory-2",
        created_at=base_time,
        importance=MemoryImportance.HIGH,
    )
    high_new = _memory(
        "memory-3",
        created_at=base_time + timedelta(minutes=1),
        importance=MemoryImportance.HIGH,
    )
    repository.save(low_new)
    repository.save(high_old)
    repository.save(high_new)

    results = repository.search(MemoryQuery(ticker="NVDA", limit=2))

    assert results == (
        MemorySearchResult(memory=high_new, relevance_score=1.0),
        MemorySearchResult(memory=high_old, relevance_score=1.0),
    )


def test_blank_memory_id_validation_through_get_and_delete() -> None:
    repository = InMemoryCommitteeMemoryRepository()

    with pytest.raises(ValueError, match="memory_id cannot be blank"):
        repository.get(" ")

    with pytest.raises(ValueError, match="memory_id cannot be blank"):
        repository.delete(" ")


def test_positive_limit_validation() -> None:
    repository = InMemoryCommitteeMemoryRepository()

    with pytest.raises(ValueError, match="limit must be positive"):
        repository.list_recent(limit=0)
