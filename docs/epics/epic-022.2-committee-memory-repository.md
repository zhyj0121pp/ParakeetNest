# Epic 22.2: Committee Memory Repository Interface

## Status

Completed.

## Purpose

Epic 22.2 adds the repository abstraction for committee memory. The goal is to
give the Investment Secretary and future memory-aware committee workflows a
stable contract for saving, reading, searching, deleting, and listing memories
before any persistence backend is introduced.

## Architecture Role

The repository interface lives in `parakeetnest.committee.memory.repository`,
beside the committee memory domain models from Epic 22.1.

`CommitteeMemoryRepository` is an abstract boundary between committee memory
domain objects and future storage implementations. Committee code should depend
on this contract rather than a concrete SQLite repository, embedding index, or
runtime-specific adapter.

The interface reinforces the core architecture principle that the committee
remembers before it reasons, while keeping memory storage and retrieval
implementation details outside the domain layer.

## Repository Contract

Implementations must provide:

- `save(memory: CommitteeMemory) -> CommitteeMemory`;
- `get(memory_id: str) -> CommitteeMemory | None`;
- `search(query: MemoryQuery) -> tuple[MemorySearchResult, ...]`;
- `delete(memory_id: str) -> bool`;
- `list_recent(limit: int = 20) -> tuple[CommitteeMemory, ...]`.

The module also provides small validation helpers:

- `validate_memory_id(memory_id: str) -> str`, which strips and rejects blank
  memory identifiers;
- `validate_positive_limit(limit: int) -> int`, which rejects non-positive
  limits.

## Intentionally Excluded

This epic intentionally does not implement:

- SQLite repositories;
- in-memory repositories;
- embeddings;
- vector search;
- ranking algorithms;
- migrations or schemas;
- prompt injection;
- committee runtime integration;
- automatic trading.

Tests use a small fake repository only to verify the interface contract. That
fake is not application persistence.

## Next Step

The next step is an in-memory implementation of `CommitteeMemoryRepository`.
That implementation can support early runtime experiments and contract tests
without committing to SQLite storage details too early.
