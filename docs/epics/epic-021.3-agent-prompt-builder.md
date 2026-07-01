# Epic 21.3: Agent Prompt Builder

## Status

Completed.

## Summary

Epic 21.3 adds a provider-neutral prompt builder for ADR-004 agent profiles.
The builder constructs deterministic system prompts from immutable
`AgentProfile` metadata only.

## Scope

The implementation adds:

- `AgentPromptBuilder`, a prompt builder abstraction;
- `DefaultAgentPromptBuilder`, the metadata-only default implementation;
- deterministic prompt sections for identity, role, mandate, capabilities,
  research guardrails, and output schema metadata.

The builder intentionally does not:

- call LLMs;
- access memory;
- access providers;
- access runtime state;
- access databases;
- access meeting context;
- change committee behavior.

## Architecture Notes

Agent prompt building is separate from the existing runtime prompt renderer.
Epic 21.3 prepares the ADR-004 migration path without wiring the new builder
into committee execution.

The default builder returns a plain string with stable section ordering. It
uses only values already present on `AgentProfile` and its nested output schema
metadata.

## Verification

Unit tests cover:

- prompt generation;
- required sections;
- deterministic output;
- different default agent profiles;
- exclusion of runtime context, prompt files, and memory/context metadata.
