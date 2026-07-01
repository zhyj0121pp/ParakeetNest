"""Tests for committee memory domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from parakeetnest.committee.memory import (
    CommitteeMemory,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)


def _memory() -> CommitteeMemory:
    return CommitteeMemory(
        memory_id="memory-1",
        scope=MemoryScope.AGENT,
        memory_type=MemoryType.AGENT_OBSERVATION,
        importance=MemoryImportance.HIGH,
        content="Xixi noted durable margin expansion.",
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        meeting_id="meeting-1",
        agent_id="xixi",
        ticker="nvda",
        topic="AI infrastructure margins",
        tags=("margins", "AI"),
        metadata={"source": "unit_test"},
    )


def test_committee_memory_creation_normalizes_fields_and_is_immutable() -> None:
    memory = CommitteeMemory(
        memory_id=" memory-1 ",
        scope="agent",
        memory_type="agent_observation",
        importance=3,
        content=" Durable margin expansion. ",
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        meeting_id=" meeting-1 ",
        agent_id=" xixi ",
        ticker=" nvda ",
        topic=" AI infrastructure margins ",
        tags=[" margins ", "AI"],  # type: ignore[arg-type]
        metadata={"source": "unit_test"},
    )

    assert memory.memory_id == "memory-1"
    assert memory.scope is MemoryScope.AGENT
    assert memory.memory_type is MemoryType.AGENT_OBSERVATION
    assert memory.importance is MemoryImportance.HIGH
    assert memory.content == "Durable margin expansion."
    assert memory.meeting_id == "meeting-1"
    assert memory.agent_id == "xixi"
    assert memory.ticker == "NVDA"
    assert memory.topic == "AI infrastructure margins"
    assert memory.tags == ("margins", "AI")

    with pytest.raises(FrozenInstanceError):
        memory.content = "Changed"


def test_committee_memory_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="content is required"):
        CommitteeMemory(
            memory_id="memory-1",
            scope=MemoryScope.COMMITTEE,
            memory_type=MemoryType.MEETING_SUMMARY,
            importance=MemoryImportance.MEDIUM,
            content=" ",
            created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        )


def test_committee_memory_defensively_copies_metadata() -> None:
    metadata = {"source": "meeting"}
    memory = CommitteeMemory(
        memory_id="memory-1",
        scope=MemoryScope.COMMITTEE,
        memory_type=MemoryType.MEETING_SUMMARY,
        importance=MemoryImportance.MEDIUM,
        content="Committee reviewed NVDA.",
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        metadata=metadata,
    )

    metadata["source"] = "changed"

    assert memory.metadata["source"] == "meeting"
    with pytest.raises(TypeError):
        memory.metadata["source"] = "changed"  # type: ignore[index]


def test_committee_memory_normalizes_tags_to_tuple() -> None:
    memory = CommitteeMemory(
        memory_id="memory-1",
        scope=MemoryScope.WATCHLIST,
        memory_type=MemoryType.FOLLOW_UP,
        importance=MemoryImportance.LOW,
        content="Revisit after earnings.",
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        tags=[" earnings ", "watchlist"],  # type: ignore[arg-type]
    )

    assert memory.tags == ("earnings", "watchlist")

    with pytest.raises(ValueError, match="tags cannot contain blank values"):
        CommitteeMemory(
            memory_id="memory-2",
            scope=MemoryScope.WATCHLIST,
            memory_type=MemoryType.FOLLOW_UP,
            importance=MemoryImportance.LOW,
            content="Revisit after guidance.",
            created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
            tags=("guidance", " "),
        )


def test_committee_memory_helper_methods() -> None:
    agent_memory = _memory()
    committee_memory = CommitteeMemory(
        memory_id="memory-2",
        scope=MemoryScope.COMMITTEE,
        memory_type=MemoryType.DECISION,
        importance=MemoryImportance.CRITICAL,
        content="Chairman deferred final action.",
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )

    assert agent_memory.is_agent_memory()
    assert not agent_memory.is_committee_memory()
    assert agent_memory.is_high_importance()
    assert committee_memory.is_committee_memory()
    assert committee_memory.is_high_importance()


def test_with_updated_content_returns_new_memory() -> None:
    original = _memory()

    updated = original.with_updated_content("Updated after risk review.")

    assert updated is not original
    assert updated.memory_id == original.memory_id
    assert updated.content == "Updated after risk review."
    assert updated.updated_at is not None
    assert original.content == "Xixi noted durable margin expansion."
    assert original.updated_at is None

    with pytest.raises(ValueError, match="content is required"):
        original.with_updated_content(" ")


def test_memory_query_defaults_normalization_and_validation() -> None:
    query = MemoryQuery(
        scope="agent",
        memory_type="risk_flag",
        importance_at_least=MemoryImportance.HIGH,
        ticker=" aapl ",
        tags=[" margin ", "risk"],  # type: ignore[arg-type]
    )

    assert query.scope is MemoryScope.AGENT
    assert query.memory_type is MemoryType.RISK_FLAG
    assert query.importance_at_least is MemoryImportance.HIGH
    assert query.ticker == "AAPL"
    assert query.tags == ("margin", "risk")
    assert query.limit == 20

    with pytest.raises(ValueError, match="limit must be positive"):
        MemoryQuery(limit=0)


def test_memory_search_result_score_validation() -> None:
    result = MemorySearchResult(
        memory=_memory(),
        relevance_score=0.75,
        reason="Ticker and topic matched.",
    )

    assert result.relevance_score == 0.75
    assert result.reason == "Ticker and topic matched."

    with pytest.raises(ValueError, match="relevance_score"):
        MemorySearchResult(memory=_memory(), relevance_score=1.01)

    with pytest.raises(ValueError, match="relevance_score"):
        MemorySearchResult(memory=_memory(), relevance_score=-0.01)
