"""Tests for the SQLite committee memory repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from parakeetnest.committee.memory import (
    CommitteeMemory,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
    SQLiteCommitteeMemoryRepository,
)
from parakeetnest.database import (
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    run_migrations,
    session_scope,
    table_names,
)


def _repository(tmp_path: Path) -> tuple[object, object]:
    engine = create_sqlite_engine(tmp_path / "committee_memory.sqlite3")
    initialize_database(engine)
    return engine, create_session_factory(engine)


def _memory(
    memory_id: str,
    *,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    scope: MemoryScope = MemoryScope.AGENT,
    memory_type: MemoryType = MemoryType.AGENT_OBSERVATION,
    importance: MemoryImportance = MemoryImportance.MEDIUM,
    meeting_id: str | None = "meeting-1",
    agent_id: str | None = "xixi",
    ticker: str | None = "NVDA",
    topic: str | None = "AI infrastructure margins",
    tags: tuple[str, ...] = ("margins",),
    metadata: dict[str, object] | None = None,
) -> CommitteeMemory:
    return CommitteeMemory(
        memory_id=memory_id,
        scope=scope,
        memory_type=memory_type,
        importance=importance,
        content=f"Committee memory {memory_id}.",
        created_at=created_at or datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        updated_at=updated_at,
        meeting_id=meeting_id,
        agent_id=agent_id,
        ticker=ticker,
        topic=topic,
        tags=tags,
        metadata=metadata or {},
    )


def test_migrations_create_committee_memories_table(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "migration.sqlite3")

    run_migrations(engine)

    table_set = set(inspect(engine).get_table_names())
    assert "committee_memories" in table_set
    assert "committee_memories" in table_names()


def test_save_and_get(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    memory = _memory("memory-1")

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        saved = repository.save(memory)
        fetched = repository.get("memory-1")

    assert saved == memory
    assert fetched == memory


def test_save_overwrites_existing_memory_id(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    original = _memory("memory-1", importance=MemoryImportance.LOW)
    replacement = _memory("memory-1", importance=MemoryImportance.CRITICAL)

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(original)
        repository.save(replacement)
        fetched = repository.get("memory-1")
        recent = repository.list_recent()

    assert fetched == replacement
    assert recent == (replacement,)


def test_delete_existing_and_missing(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(_memory("memory-1"))
        assert repository.delete("memory-1")
        assert repository.get("memory-1") is None
        assert not repository.delete("memory-1")


def test_list_recent_ordering(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    base_time = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    oldest = _memory("memory-1", created_at=base_time)
    newest = _memory("memory-2", created_at=base_time + timedelta(minutes=2))
    middle = _memory("memory-3", created_at=base_time + timedelta(minutes=1))

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(oldest)
        repository.save(newest)
        repository.save(middle)
        recent = repository.list_recent(limit=2)

    assert recent == (newest, middle)


def test_search_by_ticker(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    nvda = _memory("memory-1", ticker="NVDA")
    aapl = _memory("memory-2", ticker="AAPL")

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(nvda)
        repository.save(aapl)
        results = repository.search(MemoryQuery(ticker="nvda"))

    assert results == (MemorySearchResult(memory=nvda, relevance_score=1.0),)


def test_search_by_meeting_id(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    matching = _memory("memory-1", meeting_id="meeting-2")
    other = _memory("memory-2", meeting_id="meeting-1")

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(matching)
        repository.save(other)
        results = repository.search(MemoryQuery(meeting_id="meeting-2"))

    assert results == (MemorySearchResult(memory=matching, relevance_score=1.0),)


def test_search_by_agent_id(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    xixi = _memory("memory-1", agent_id="xixi")
    yoyo = _memory("memory-2", agent_id="yoyo")

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(xixi)
        repository.save(yoyo)
        results = repository.search(MemoryQuery(agent_id="yoyo"))

    assert results == (MemorySearchResult(memory=yoyo, relevance_score=1.0),)


def test_search_by_importance_at_least(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    low = _memory("memory-1", importance=MemoryImportance.LOW)
    high = _memory("memory-2", importance=MemoryImportance.HIGH)
    critical = _memory("memory-3", importance=MemoryImportance.CRITICAL)

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(low)
        repository.save(high)
        repository.save(critical)
        results = repository.search(
            MemoryQuery(importance_at_least=MemoryImportance.HIGH)
        )

    assert results == (
        MemorySearchResult(memory=critical, relevance_score=1.0),
        MemorySearchResult(memory=high, relevance_score=1.0),
    )


def test_search_by_tags(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    matching = _memory("memory-1", tags=("margins", "earnings", "watchlist"))
    partial = _memory("memory-2", tags=("margins",))

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(matching)
        repository.save(partial)
        results = repository.search(MemoryQuery(tags=("margins", "earnings")))

    assert results == (MemorySearchResult(memory=matching, relevance_score=1.0),)


def test_metadata_round_trip(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    memory = _memory(
        "memory-1",
        metadata={"source": "chairman", "scores": {"quality": 0.9}, "ids": [1, 2]},
    )

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(memory)
        fetched = repository.get("memory-1")

    assert fetched is not None
    assert dict(fetched.metadata) == {
        "source": "chairman",
        "scores": {"quality": 0.9},
        "ids": [1, 2],
    }


def test_updated_at_round_trip(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)
    updated_at = datetime(2026, 7, 1, 12, 5, tzinfo=UTC)
    memory = _memory("memory-1", updated_at=updated_at)

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        repository.save(memory)
        fetched = repository.get("memory-1")

    assert fetched is not None
    assert fetched.updated_at == updated_at


def test_blank_memory_id_validation(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        with pytest.raises(ValueError, match="memory_id cannot be blank"):
            repository.get(" ")
        with pytest.raises(ValueError, match="memory_id cannot be blank"):
            repository.delete(" ")


def test_positive_limit_validation(tmp_path: Path) -> None:
    _, session_factory = _repository(tmp_path)

    with session_scope(session_factory) as session:
        repository = SQLiteCommitteeMemoryRepository(session)
        with pytest.raises(ValueError, match="limit must be positive"):
            repository.list_recent(limit=0)
