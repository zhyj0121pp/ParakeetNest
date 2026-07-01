# Epic 21.1: Agent Profile Model

## Status

Completed.

## Summary

Epic 21.1 introduces the domain model foundation for ADR-004's agent-first
committee architecture.

This epic adds immutable, provider-neutral committee agent profile models for:

- `AgentProfile`;
- `AgentRole`;
- `AgentContextRequirement`;
- `AgentMemoryPolicy`;
- `AgentOutputSchema`.

Initial metadata-only profiles are defined for:

- Xixi, Chief Fundamental Analyst;
- Dongdong, Chief Opportunity Hunter;
- Yoyo, Chief Risk Officer;
- Chairman, final decision maker.

## Scope

This epic is domain-model only. Profiles describe identity, mandate, prompt
source, context needs, memory policy, output contract, capabilities, guardrails,
and version metadata.

The implementation intentionally does not add:

- agent registry;
- agent runtime changes;
- prompt builder changes;
- memory integration;
- CIO decision engine;
- committee orchestrator changes;
- LLM calls or provider access.

## Architecture Notes

Agent profiles are durable metadata. They can be inspected, serialized, tested,
and later registered, but they do not execute behavior.

The existing committee continues to work unchanged. Runtime-oriented classes
remain separate from profile metadata until later ADR-004 migration epics.

## Verification

Unit tests cover:

- model creation and normalization;
- validation failures;
- immutability;
- equality;
- serialization round-trips;
- default profile metadata;
- Chairman recommendation contract metadata.
