# Epic 22.1: Committee Memory Domain Models

## Status

Completed.

## Purpose

Epic 22.1 establishes the domain model foundation for committee memory. It gives
the Investment Secretary and future memory services a stable vocabulary for
recording what the committee learned before any persistence, retrieval, or
runtime integration is introduced.

## Architecture Role

Committee memory models live in `parakeetnest.committee.memory`, close to the
agent-first committee architecture and separate from the older general
investment knowledge base.

The models are frozen dataclasses with enum-backed fields, normalized tags, and
defensive metadata copies. They are designed to be passed between future memory
repositories, retrieval engines, prompt builders, and committee runtime wiring
without owning those responsibilities.

## Included

This epic adds:

- `MemoryScope`;
- `MemoryType`;
- `MemoryImportance`;
- `CommitteeMemory`;
- `MemoryQuery`;
- `MemorySearchResult`.

`CommitteeMemory` captures scoped memory content, meeting and agent links,
optional ticker/topic metadata, tags, and caller-supplied metadata.

`MemoryQuery` captures optional future retrieval filters with a positive default
limit.

`MemorySearchResult` wraps a memory with a normalized relevance score and an
optional explanation.

## Intentionally Excluded

This epic intentionally does not implement:

- repositories;
- SQLite tables or migrations;
- database access;
- search or ranking engines;
- embeddings;
- prompt injection;
- agent runtime integration;
- committee orchestrator integration.

## Follow-up Epics

Likely follow-up work includes:

- committee memory repository and SQLite persistence;
- memory retrieval and ranking services;
- memory-aware prompt building for Xixi, Dongdong, Yoyo, and Chairman;
- Investment Secretary write paths from meeting outputs;
- committee runtime integration with explicit memory read and write phases;
- safeguards for stale, conflicting, or low-confidence memory.
