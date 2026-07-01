# Epic 019: Committee Integration

Status: Epic 19 - Completed

## Purpose

Integrate the unified Investment Intelligence Context from Epic 18 into the
committee meeting flow without changing the frozen v1.1 architecture.

The committee remembers before it reasons. Epic 19 makes the completed
investment intelligence layer available to Xixi, Dongdong, Yoyo, and the
Chairman as rendered prompt context before any agent executes.

## Architecture

Epic 19 keeps data fetching and signal calculation outside committee agents.
Meeting orchestration coordinates context assembly:

```text
ContextService -> MeetingContext
InvestmentIntelligenceContextService -> InvestmentIntelligenceContext
InvestmentIntelligenceRenderer -> Markdown
MeetingService -> CommitteeMeetingOrchestrator -> AgentRuntime -> Prompt
```

Committee agents consume rendered context only. They do not depend on market
data, news, macro, risk, sentiment, health, or provider services.

## Implementation

- `MeetingService` now accepts an optional
  `InvestmentIntelligenceContextService` and renderer through constructor
  injection.
- Investment intelligence is built and rendered before the orchestrator starts
  agent execution.
- `CommitteeMeetingOrchestrator` forwards the rendered Markdown through the
  per-agent `MeetingContext`.
- `PromptRenderer` adds an `Investment intelligence context` section to every
  agent prompt.
- `create_app()` wires the deterministic
  `MockInvestmentIntelligenceService`, keeping local and test runs free of
  external API calls.

The integration remains optional. If no investment intelligence service is
provided, existing non-investment context behavior continues and prompts include
a deterministic empty investment-intelligence section.

## Tests

Coverage proves:

- committee meetings can include investment intelligence context;
- agents receive the rendered intelligence context in their prompt;
- existing non-investment context behavior still works;
- mock services run end-to-end without external APIs;
- committee/runtime boundary tests still prevent direct provider access.

## Out of Scope

Epic 19 intentionally excludes:

- automatic trading;
- direct agent access to market, news, macro, risk, sentiment, or health
  providers;
- new external data providers;
- persistence of the rendered investment intelligence artifact;
- changes to the frozen v1.1 service and context boundaries.
