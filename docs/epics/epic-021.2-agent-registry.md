# Epic 21.2: Agent Registry

## Status

Completed.

## Summary

Epic 21.2 adds a provider-neutral registry for ADR-004 agent profiles. The
registry manages `AgentProfile` objects only: it provides stable lookup,
listing, existence checks, and registration for committee role metadata.

## Scope

The implementation adds:

- `AgentRegistry`, a profile registry abstraction;
- `InMemoryAgentRegistry`, backed by `DEFAULT_AGENT_PROFILES`;
- clear exceptions for unknown and duplicate agent IDs;
- a default registry factory for the initial committee profiles.

The registry intentionally does not:

- create runtimes;
- call LLMs;
- render prompts;
- access providers;
- access memory;
- access databases;
- change committee behavior.

## Architecture Notes

Agent registry ownership stops at profile discovery and selection. It stores
immutable `AgentProfile` objects in registration order and returns those objects
without constructing runtime collaborators.

Unknown agent IDs fail early with `UnknownAgentProfileError`. Duplicate
registrations fail with `DuplicateAgentProfileError`.

## Verification

Unit tests cover:

- profile lookup;
- registration;
- duplicate registration;
- unknown IDs;
- existence checks;
- iteration/listing order.
