"""SQLite-backed committee memory repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from parakeetnest.committee.memory.models import (
    CommitteeMemory,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)
from parakeetnest.committee.memory.repository import (
    CommitteeMemoryRepository,
    validate_memory_id,
    validate_positive_limit,
)
from parakeetnest.database.models import CommitteeMemoryRecord


class SQLiteCommitteeMemoryRepository(CommitteeMemoryRepository):
    """SQLAlchemy repository for durable committee memory records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active SQLAlchemy session."""
        self.session = session

    def save(self, memory: CommitteeMemory) -> CommitteeMemory:
        """Persist a committee memory and return the saved domain object."""
        memory_id = validate_memory_id(memory.memory_id)
        self.session.merge(_to_record(memory, memory_id=memory_id))
        self.session.flush()
        return memory

    def get(self, memory_id: str) -> CommitteeMemory | None:
        """Return one committee memory by identifier, if it exists."""
        record = self.session.get(CommitteeMemoryRecord, validate_memory_id(memory_id))
        return None if record is None else _to_memory(record)

    def search(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        """Return deterministically ranked memories matching exact filters."""
        limit = validate_positive_limit(query.limit)
        statement = select(CommitteeMemoryRecord)

        if query.scope is not None:
            statement = statement.where(CommitteeMemoryRecord.scope == query.scope.value)
        if query.memory_type is not None:
            statement = statement.where(
                CommitteeMemoryRecord.memory_type == query.memory_type.value
            )
        if query.importance_at_least is not None:
            statement = statement.where(
                CommitteeMemoryRecord.importance >= int(query.importance_at_least)
            )
        if query.meeting_id is not None:
            statement = statement.where(CommitteeMemoryRecord.meeting_id == query.meeting_id)
        if query.agent_id is not None:
            statement = statement.where(CommitteeMemoryRecord.agent_id == query.agent_id)
        if query.ticker is not None:
            statement = statement.where(CommitteeMemoryRecord.ticker == query.ticker)
        if query.topic is not None:
            statement = statement.where(CommitteeMemoryRecord.topic == query.topic)

        statement = statement.order_by(
            CommitteeMemoryRecord.importance.desc(),
            CommitteeMemoryRecord.created_at.desc(),
            CommitteeMemoryRecord.memory_id.desc(),
        )
        if not query.tags:
            statement = statement.limit(limit)

        memories = (_to_memory(record) for record in self.session.scalars(statement).all())
        matches = (memory for memory in memories if _matches_tags(memory, query.tags))
        return tuple(
            MemorySearchResult(memory=memory, relevance_score=1.0)
            for memory in list(matches)[:limit]
        )

    def delete(self, memory_id: str) -> bool:
        """Delete one committee memory by identifier."""
        statement = delete(CommitteeMemoryRecord).where(
            CommitteeMemoryRecord.memory_id == validate_memory_id(memory_id)
        )
        result = self.session.execute(statement)
        self.session.flush()
        return result.rowcount == 1

    def list_recent(self, limit: int = 20) -> tuple[CommitteeMemory, ...]:
        """Return most recently created committee memories."""
        validated_limit = validate_positive_limit(limit)
        statement = (
            select(CommitteeMemoryRecord)
            .order_by(
                CommitteeMemoryRecord.created_at.desc(),
                CommitteeMemoryRecord.memory_id.desc(),
            )
            .limit(validated_limit)
        )
        return tuple(_to_memory(record) for record in self.session.scalars(statement).all())


def _to_record(memory: CommitteeMemory, *, memory_id: str) -> CommitteeMemoryRecord:
    return CommitteeMemoryRecord(
        memory_id=memory_id,
        scope=memory.scope.value,
        memory_type=memory.memory_type.value,
        importance=int(memory.importance),
        content=memory.content,
        created_at=_to_utc_iso(memory.created_at),
        updated_at=None if memory.updated_at is None else _to_utc_iso(memory.updated_at),
        meeting_id=memory.meeting_id,
        agent_id=memory.agent_id,
        ticker=memory.ticker,
        topic=memory.topic,
        tags_json=list(memory.tags),
        metadata_json=dict(memory.metadata),
    )


def _to_memory(record: CommitteeMemoryRecord) -> CommitteeMemory:
    return CommitteeMemory(
        memory_id=record.memory_id,
        scope=MemoryScope(record.scope),
        memory_type=MemoryType(record.memory_type),
        importance=MemoryImportance(record.importance),
        content=record.content,
        created_at=_from_iso(record.created_at),
        updated_at=None if record.updated_at is None else _from_iso(record.updated_at),
        meeting_id=record.meeting_id,
        agent_id=record.agent_id,
        ticker=record.ticker,
        topic=record.topic,
        tags=tuple(record.tags_json),
        metadata=_metadata(record.metadata_json),
    )


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _matches_tags(memory: CommitteeMemory, tags: tuple[str, ...]) -> bool:
    return all(tag in memory.tags for tag in tags)


__all__ = ["SQLiteCommitteeMemoryRepository"]
