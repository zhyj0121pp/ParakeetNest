# Epic 22.8: Application Memory Wiring

## Status

Completed.

## Purpose

Epic 22.8 wires committee memory into application composition so real
ParakeetNest runtime flows can remember before they reason and write useful
meeting output back to durable storage.

Earlier Epic 22 work introduced the memory domain model, repository contract,
service boundary, prompt-time memory context, best-effort write-back, and the
SQLite repository. This epic connects those pieces in the application bootstrap.

## Architecture Role

Application bootstrap is the only place that chooses the concrete durable
memory repository.

```text
create_app()
        |
SQLAlchemy Session
        |
SQLiteCommitteeMemoryRepository
        |
CommitteeMemoryService
        |
AgentRuntime + CommitteeMeetingOrchestrator
```

`AgentRuntime` and `CommitteeMeetingOrchestrator` receive
`CommitteeMemoryService`. They do not depend on SQLite, SQLAlchemy repository
details, migrations, or storage configuration.

## Composition Flow

When `create_app()` creates the application-owned SQLAlchemy session, it also
creates:

- `SQLiteCommitteeMemoryRepository(session)`
- `CommitteeMemoryService(memory_repository)`

The same `CommitteeMemoryService` instance is passed into:

- `AgentRuntime`, for prompt-time memory context;
- `CommitteeMeetingOrchestrator`, for completed-meeting write-back.

The app container exposes `memory_service` so callers can seed, inspect, or
manage committee memory through the service boundary.

## Durable Memory Behavior

During agent execution, `AgentRuntime` asks `CommitteeMemoryService` for
relevant memories and includes the existing memory context in prompts when
matches are found.

After a meeting completes, `CommitteeMeetingOrchestrator` writes back:

- a meeting summary;
- a decision memory when the Chairman output includes an action or decision;
- agent observations for results that include an agent id and ticker.

Because the service is backed by `SQLiteCommitteeMemoryRepository` in
application composition, these records are stored in the `committee_memories`
table and can be read by later app runs that use the same database.

## Intentionally Excluded

This epic intentionally does not implement:

- embeddings;
- vector search;
- portfolio committee workflows;
- watchlist intelligence;
- automatic trading or trading execution;
- new prompt changes beyond the existing memory context block;
- new memory ranking beyond repository-supported deterministic search.

## Next Step

The next step is to decide which product flows should seed or curate committee
memory before meetings, while keeping retrieval behind `CommitteeMemoryService`
and leaving trading execution out of scope.
