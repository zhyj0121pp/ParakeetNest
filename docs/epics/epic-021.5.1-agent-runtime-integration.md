# Epic 21.5.1: Agent Runtime Committee Integration

## Status

Completed.

## Summary

Epic 21.5.1 integrates the provider-neutral Agent Runtime into the existing
persistent committee execution flow as an adapter migration.

The committee now prepares each agent turn, executes it through
`parakeetnest.committee.agent_runtime.DefaultAgentRuntime`, then parses the
response into the same persisted `AgentResult` shape used before this epic.

## Scope

This epic intentionally preserves the existing committee flow:

- Xixi, Dongdong, Yoyo, and Chairman still execute one at a time in the same
  order;
- the orchestrator still owns meeting flow and message persistence;
- previous agent results are still passed into later prompts;
- voting, chairman logic, memory, portfolio logic, and meeting finalization are
  unchanged;
- the LLM provider remains behind the runtime boundary.

## Architecture Notes

`parakeetnest.committee.runtime.AgentRuntime` is now the committee-facing
adapter. It renders the existing prompt, creates an `AgentRequest`, delegates
execution to the provider-neutral runtime, and applies the existing output
parser and JSON schemas.

`DefaultAgentRuntime` accepts an optional output-schema registry keyed by
`AgentRequest.output_schema_id`. This preserves schema-aware provider behavior
for committee opinions and chairman summaries while keeping the runtime focused
on one prepared agent turn.

## Verification

Regression tests prove the migrated adapter returns the same committee
`AgentResult` as the previous direct provider path for the same prompt,
schema, and model response.

The complete test suite was run for this epic.
