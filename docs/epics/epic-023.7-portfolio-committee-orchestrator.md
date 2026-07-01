# Epic 23.7 - Portfolio Committee Orchestrator

## Goal

Create a portfolio-specific committee orchestration entry point that uses the existing committee agent runtime and portfolio context provider architecture.

## Scope

- Add `PortfolioCommitteeOrchestrator` in `src/parakeetnest/portfolio/orchestrator.py`.
- Build portfolio committee context through the existing context provider contract.
- Run the portfolio committee agents through the shared committee `AgentRuntime`.
- Return a structured advisory committee result with metadata and collected agent responses.
- Keep memory integration consistent with the existing committee runtime by passing through the runtime memory service when present.

## Non-Goals

- No Robinhood integration.
- No brokerage API.
- No real trading.
- No order placement.
- No trade execution.
- No automatic buy or sell action.
- No portfolio rebalancing execution.
- No recommendation engine beyond advisory committee output.
- No database schema changes.
- No CLI runner yet.

## Architecture Notes

The portfolio orchestrator is not a separate architecture. It reuses:

- `ContextRequest` and portfolio context provider output from the Context Layer.
- `MeetingContext` and `AgentResult` from the committee domain.
- `AgentRuntime` for prompt rendering, memory-aware context, LLM execution, and parsing.
- Portfolio committee agent profiles from Epic 23.6.

The result is intentionally in-memory and advisory. Persistence remains the responsibility of application services that choose to wrap this entry point later.

## Orchestration Flow

1. Receive a portfolio review question.
2. Build a `ContextRequest` with portfolio context enabled.
3. Ask the portfolio context provider for the current portfolio context.
4. Run portfolio committee agents in deterministic order.
5. Pass prior agent outputs into later agent turns through `MeetingContext.previous_agent_results`.
6. Return `PortfolioCommitteeResult` with status, metadata, context, and all agent responses.

## Agent List

- Portfolio Manager
- Portfolio Risk Manager
- Sector Analyst
- Macro Strategist

## Validation Checklist

- Orchestrator can be created.
- Portfolio context provider is called.
- All portfolio agents are run.
- Agent responses are collected.
- Result includes portfolio committee metadata.
- Memory service remains optional and follows existing runtime integration.
- Provider and context errors propagate clearly.
- No trade execution, order placement, brokerage, Robinhood, or automatic trading behavior exists.
