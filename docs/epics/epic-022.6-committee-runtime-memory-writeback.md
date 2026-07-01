# Epic 22.6: Committee Runtime Memory Write-Back

## Status

Completed.

## Purpose

Epic 22.6 adds best-effort memory write-back after a prompt-backed committee
meeting finishes.

Epic 22.5 made prior committee memory available before reasoning. This epic
closes the loop by saving useful outputs from the completed meeting through
`CommitteeMemoryService`, while keeping durable storage out of the runtime.

## Architecture Role

The integration lives in `parakeetnest.committee.orchestrator`.

`CommitteeMeetingOrchestrator` accepts an optional `CommitteeMemoryService`.
When omitted, meeting behavior is unchanged. When the orchestrator is built
with an `AgentRuntime` that already has a memory service, the orchestrator uses
that same service for write-back.

```text
CommitteeMeetingOrchestrator.run()
        |
agent execution and meeting messages
        |
MeetingResult assembled
        |
CommitteeMemoryService write-back
        |
CommitteeMemoryRepository
```

The orchestrator depends on the service boundary only. It does not know about
SQLite, migrations, embeddings, or retrieval implementation details.

## Write-Back Timing

Memory write-back happens only after all agents have executed and the final
`MeetingResult` has been assembled from the Chairman output.

No memory is written before or during agent execution. This preserves the core
sequence:

```text
remember before reasoning -> agents reason -> Chairman concludes -> save memories
```

## Persisted Memories

When available, the runtime saves:

- a meeting summary memory from Chairman `summary`, `rationale`, or
  `conclusion` content;
- a decision memory from Chairman action or decision payload fields;
- one agent observation memory for each agent result that includes `agent_id`
  and `ticker`.

Agent observation content is the raw agent result content. The runtime does not
summarize, rewrite, enrich, or embed observations.

## Failure Policy

Memory write-back is best-effort. If memory persistence fails, the orchestrator
logs a warning and returns the successful meeting result.

This keeps memory storage from turning a completed committee meeting into a
failed meeting. Agent execution failures still propagate through the existing
meeting failure path.

The orchestrator tracks meetings that have already completed write-back in the
current process so the same orchestrator instance does not duplicate memory
writes for the same meeting id.

## Intentionally Excluded

This epic intentionally does not implement:

- SQLite-backed committee memory persistence;
- database migrations;
- embeddings;
- vector search;
- automatic summarization;
- trading execution;
- portfolio committee workflows;
- new memory ranking or retrieval behavior.

## Next Step

The next step is a SQLite-backed `CommitteeMemoryRepository` so runtime
write-back can become durable without changing the orchestrator or agent
runtime service boundary.
