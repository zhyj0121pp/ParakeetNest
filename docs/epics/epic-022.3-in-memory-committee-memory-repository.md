# Epic 22.3: In-Memory Committee Memory Repository

## Status

Completed.

## Purpose

Epic 22.3 adds a concrete in-memory implementation of
`CommitteeMemoryRepository` for tests, local development, and early runtime
experiments. It gives the committee memory layer a usable repository while the
storage model remains intentionally simple.

## Architecture Role

`InMemoryCommitteeMemoryRepository` lives in
`parakeetnest.committee.memory.in_memory_repository` and implements the
repository contract introduced in Epic 22.2.

The implementation is process-local and stores immutable `CommitteeMemory`
records in a dictionary keyed by `memory_id`. Committee code can depend on the
repository interface while tests and early integrations use this concrete class
without introducing SQLite details too early.

## Search Behavior

Search is exact-match and deterministic. It filters by:

- `scope`;
- `memory_type`;
- `importance_at_least`;
- `meeting_id`;
- `agent_id`;
- `ticker`;
- `topic`;
- `tags`.

All requested tags must be present on a memory. Results are ranked by higher
importance first, then newer `created_at` first, and limited by `MemoryQuery`.
Each result receives a `relevance_score` of `1.0` because this repository does
not compute semantic relevance.

## Why This Exists Before SQLite

The in-memory repository lets the Investment Secretary and memory-aware
committee flows be developed against a real repository implementation before
schema, migrations, and persistence tradeoffs are finalized. It keeps Epic 22
moving in small, testable modules while preserving the future SQLite boundary.

## Intentionally Excluded

This epic intentionally does not implement:

- SQLite storage;
- database migrations;
- embeddings;
- vector search;
- runtime integration;
- prompt injection;
- automatic trading.

## Next Step

The next step is `MemoryService`, which can coordinate repository access and
prepare committee memory retrieval for higher-level workflows.
