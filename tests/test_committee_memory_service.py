"""Tests for the committee memory application service."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.committee.memory import (
    CommitteeMemory,
    CommitteeMemoryService,
    InMemoryCommitteeMemoryRepository,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)


def _memory(memory_id: str = "memory-1") -> CommitteeMemory:
    return CommitteeMemory(
        memory_id=memory_id,
        scope=MemoryScope.COMMITTEE,
        memory_type=MemoryType.MEETING_SUMMARY,
        importance=MemoryImportance.HIGH,
        content="The committee debated NVDA margin durability.",
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        meeting_id="meeting-1",
    )


def test_save_memory_delegates_to_repository() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)
    memory = _memory()

    saved = service.save_memory(memory)

    assert saved == memory
    assert repository.get(memory.memory_id) == memory


def test_save_meeting_summary_creates_committee_memory() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)

    saved = service.save_meeting_summary(
        meeting_id="meeting-1",
        content="Chairman approved a watchlist follow-up.",
        metadata={"source": "committee"},
    )

    assert saved.memory_id
    assert saved.scope is MemoryScope.COMMITTEE
    assert saved.memory_type is MemoryType.MEETING_SUMMARY
    assert saved.importance is MemoryImportance.HIGH
    assert saved.content == "Chairman approved a watchlist follow-up."
    assert saved.meeting_id == "meeting-1"
    assert saved.metadata["source"] == "committee"
    assert saved.created_at.tzinfo is UTC
    assert repository.get(saved.memory_id) == saved


def test_save_agent_observation_creates_agent_memory() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)

    saved = service.save_agent_observation(
        meeting_id="meeting-1",
        agent_id="xixi",
        ticker="nvda",
        content="Xixi noted gross margin resilience.",
    )

    assert saved.memory_id
    assert saved.scope is MemoryScope.AGENT
    assert saved.memory_type is MemoryType.AGENT_OBSERVATION
    assert saved.importance is MemoryImportance.MEDIUM
    assert saved.meeting_id == "meeting-1"
    assert saved.agent_id == "xixi"
    assert saved.ticker == "NVDA"
    assert saved.created_at.tzinfo is UTC
    assert repository.get(saved.memory_id) == saved


def test_save_decision_creates_committee_decision() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)

    saved = service.save_decision(
        meeting_id="meeting-1",
        content="Maintain HOLD pending earnings catalyst confirmation.",
    )

    assert saved.memory_id
    assert saved.scope is MemoryScope.COMMITTEE
    assert saved.memory_type is MemoryType.DECISION
    assert saved.importance is MemoryImportance.CRITICAL
    assert saved.meeting_id == "meeting-1"
    assert saved.content == "Maintain HOLD pending earnings catalyst confirmation."
    assert saved.created_at.tzinfo is UTC
    assert repository.get(saved.memory_id) == saved


def test_search_delegates_to_repository() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)
    memory = service.save_agent_observation(
        meeting_id="meeting-1",
        agent_id="dongdong",
        ticker="TSLA",
        content="Dongdong saw improving opportunity setup.",
    )

    results = service.search(MemoryQuery(ticker="tsla"))

    assert results == (MemorySearchResult(memory=memory, relevance_score=1.0),)


def test_delete_delegates_to_repository() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)
    memory = service.save_memory(_memory())

    assert service.delete_memory(memory.memory_id)
    assert repository.get(memory.memory_id) is None


def test_list_recent_delegates_to_repository() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)
    older = service.save_memory(_memory("memory-1"))
    newer = service.save_meeting_summary(
        meeting_id="meeting-2",
        content="Newer meeting summary.",
    )

    assert service.list_recent(limit=1) == (newer,)
    assert older in service.list_recent(limit=2)


def test_get_memory_delegates_to_repository() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    service = CommitteeMemoryService(repository)
    memory = service.save_memory(_memory())

    assert service.get_memory(memory.memory_id) == memory
    assert service.get_memory("missing-memory") is None
