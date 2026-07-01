# Epic 22.5: Committee Runtime Memory Context

## Status

Completed.

## Purpose

Epic 22.5 wires `CommitteeMemoryService` into the prompt-backed committee
runtime as a read-only context provider.

The committee remembers before it reasons. This epic lets Xixi, Dongdong,
Yoyo, and the Chairman receive relevant prior committee memories before agent
execution while preserving the existing runtime flow.

## Architecture Role

The integration lives in `parakeetnest.committee.runtime`.

`AgentRuntime` can optionally carry a `CommitteeMemoryService`. When present,
`PromptRenderer` asks the service for relevant memories before rendering the
agent prompt:

```text
CommitteeMeetingOrchestrator
        |
AgentRuntime
        |
PromptRenderer
        |
CommitteeMemoryService.search()
        |
CommitteeMemoryRepository
```

The memory block is injected through the existing profile-backed prompt
builder. No agent calls memory services directly.

## Read-Only Memory Behavior

For each agent turn, the runtime searches for medium-or-higher memories using:

- ticker when available;
- meeting id when available;
- the active agent id for the agent-specific query;
- `importance_at_least = MemoryImportance.MEDIUM`;
- `limit = 10`.

The renderer performs one general memory query and one agent-specific query,
deduplicates by memory id, and renders at most 10 memories.

When memories are found, the prompt includes a plain text block:

```text
Relevant Committee Memories:
- [HIGH][MEETING_SUMMARY] Previous committee preferred HOLD until earnings.
- [MEDIUM][AGENT_OBSERVATION][xixi] Xixi noted margin resilience.
```

If no `CommitteeMemoryService` is provided, the runtime behaves as before. If
search returns no memories, the memory block is omitted.

## Intentionally Excluded

This epic intentionally does not implement:

- SQLite repository work;
- database migrations;
- memory write-back from runtime;
- automatic summarization;
- Investment Secretary workflows;
- embeddings;
- vector search;
- trading decisions or automatic trading.

## Next Step

The next step can add runtime memory write-back after committee execution or a
SQLite-backed `CommitteeMemoryRepository`. Either should keep the runtime
dependent on `CommitteeMemoryService` rather than storage details.
