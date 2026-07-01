# Epic 22.7: SQLite Committee Memory Repository

## Status

Completed.

## Purpose

Epic 22.7 adds durable SQLite-backed persistence for committee memory records.

Earlier Epic 22 work introduced the memory domain model, repository contract,
in-memory repository, service boundary, runtime memory context, and best-effort
write-back. This epic makes those memories durable without changing the
committee runtime or prompt flow.

## Architecture Role

`SQLiteCommitteeMemoryRepository` lives in
`parakeetnest.committee.memory.sqlite_repository`.

It implements `CommitteeMemoryRepository` and depends on a caller-provided
SQLAlchemy `Session`, matching the existing ParakeetNest SQLite repository
style.

```text
CommitteeMemoryService
        |
CommitteeMemoryRepository
        |
SQLiteCommitteeMemoryRepository
        |
committee_memories table
```

The committee runtime continues to depend on `CommitteeMemoryService`, not on
SQLite details.

## Schema

The SQLite table is named `committee_memories`.

Columns:

- `memory_id TEXT PRIMARY KEY`
- `scope TEXT NOT NULL`
- `memory_type TEXT NOT NULL`
- `importance INTEGER NOT NULL`
- `content TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NULL`
- `meeting_id TEXT NULL`
- `agent_id TEXT NULL`
- `ticker TEXT NULL`
- `topic TEXT NULL`
- `tags_json TEXT NOT NULL`
- `metadata_json TEXT NOT NULL`

In SQLAlchemy, `tags_json` and `metadata_json` use JSON columns so SQLite stores
portable JSON payloads while Python receives structured lists and dictionaries.

## Serialization

Enums are stored consistently as stable primitive values:

- `MemoryScope` -> string value;
- `MemoryType` -> string value;
- `MemoryImportance` -> integer value.

Datetime fields are stored as ISO 8601 UTC strings. Naive datetimes are treated
as UTC before serialization.

Tags are stored as a JSON array. Metadata is stored as a JSON object.

Rows are mapped back into immutable `CommitteeMemory` domain objects on reads,
searches, and recent listing.

## Search Behavior

The repository supports exact SQL filters for:

- `scope`
- `memory_type`
- `meeting_id`
- `agent_id`
- `ticker`
- `topic`

`importance_at_least` is applied as a SQL greater-than-or-equal filter.

Tags are filtered in Python after candidate rows are loaded. When tags are
present, the repository applies the final limit after tag matching so the
requested limit is respected.

Ranking is deterministic:

```text
importance desc, created_at desc, memory_id desc
```

`list_recent()` ranks by:

```text
created_at desc, memory_id desc
```

## Intentionally Excluded

This epic intentionally does not implement:

- embeddings;
- vector search;
- prompt changes;
- runtime changes;
- portfolio committee workflows;
- automatic trading or trading execution.

## Next Step

The next step is wiring application composition to choose
`SQLiteCommitteeMemoryRepository` where durable committee memory is desired,
while keeping tests and lightweight local flows free to use the in-memory
repository.
