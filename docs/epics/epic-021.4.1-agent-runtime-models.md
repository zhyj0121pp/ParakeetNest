# Epic 21.4.1: Agent Runtime Models

## Status

Completed.

## Summary

Epic 21.4.1 adds immutable, provider-neutral domain models for prepared
ADR-004 agent runtime turns.

The implementation adds:

- `AgentRequest`;
- `AgentResponse`;
- `AgentExecutionMetadata`;
- `AgentExecutionResult`.

## Scope

This epic is domain-model only. The models describe prepared agent requests,
agent responses, execution metadata, and persistable result envelopes.

The implementation intentionally does not:

- execute agents;
- call LLMs;
- render prompts;
- parse provider responses;
- access memory;
- access providers;
- access databases;
- integrate committee orchestration;
- change committee behavior.

## Architecture Notes

Agent runtime models live in `parakeetnest.committee.agent_runtime`, separate
from the existing executable committee runtime. They are suitable for later
ADR-004 runtime wiring without introducing a new execution path in this epic.

The models are frozen dataclasses and defensively freeze nested metadata and
parsed response payloads. Serialization follows the existing 21.x pattern with
`to_dict` and `from_dict` methods.

`AgentExecutionResult` enforces consistency between request, response, and
execution metadata agent IDs. A result may represent either a successful turn
with a response or a failed turn with an error message, but not both.

## Verification

Unit tests cover:

- creation and normalization;
- validation failures;
- immutability;
- equality;
- serialization round-trips;
- failure result envelopes.
