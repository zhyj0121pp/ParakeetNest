# Epic 22.4: Committee Memory Service

## Status

Completed.

## Purpose

Epic 22.4 introduces `CommitteeMemoryService`, the application service that
coordinates committee memory operations between committee runtime code and the
memory repository boundary.

The committee remembers before it reasons, and this service gives future
runtime flows a single place to create and retrieve durable committee memories
without learning storage details.

## Architecture Role

`CommitteeMemoryService` lives in
`parakeetnest.committee.memory.service`.

It sits between future committee runtime workflows and
`CommitteeMemoryRepository`:

```text
Committee Runtime
        |
CommitteeMemoryService
        |
CommitteeMemoryRepository
```

Runtime code can ask the service to save meeting summaries, agent observations,
and decisions. The service creates `CommitteeMemory` domain objects with
UUID-based identifiers and UTC timestamps, then delegates persistence and
retrieval to the repository contract.

## Why This Service Exists

The service keeps memory creation rules out of runtime orchestration while
keeping repository implementations focused on storage and retrieval.

It gives the platform a stable application boundary where common committee
memory operations can be expressed in domain language:

- `save_meeting_summary`;
- `save_agent_observation`;
- `save_decision`;
- `save_memory`;
- `get_memory`;
- `search`;
- `list_recent`;
- `delete_memory`.

## Responsibilities

`CommitteeMemoryService` is responsible for:

- creating `CommitteeMemory` objects for convenience APIs;
- assigning UUID-based `memory_id` values;
- assigning current UTC `created_at` timestamps;
- choosing the appropriate memory scope and type for convenience APIs;
- delegating save, get, delete, list, and search operations to
  `CommitteeMemoryRepository`.

## Intentionally Excluded

This epic intentionally does not implement:

- SQLite repositories;
- runtime integration;
- prompt injection;
- embeddings;
- Investment Secretary workflows;
- committee orchestration;
- repository-specific storage logic;
- automatic trading.

## Next Epic

The next epic can integrate this service into the committee runtime or
Investment Secretary workflow, while continuing to depend on the repository
interface instead of a concrete storage backend.
