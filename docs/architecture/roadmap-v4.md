# Roadmap v4: Portfolio Intelligence Milestone Summary

Date: 2026-07-01

Status: Portfolio Intelligence milestone complete. Ready to begin Epic 24:
Watchlist Intelligence.

Scope: Documentation summary only. No runtime behavior, provider integration,
trading capability, or production code change is included in this milestone.

## Current Architecture Status

ParakeetNest has completed Epic 23: Portfolio Committee as the first
portfolio-aware committee milestone. The system can now assemble deterministic
mock portfolio state, convert it into prompt-ready portfolio context, inject
that context into portfolio-specialist agents, and run an advisory committee
meeting through a local CLI.

The architecture remains consistent with the project principle:

```text
The committee remembers before it reasons.
```

Portfolio intelligence is advisory research only. Portfolio-aware agents may
reason about holdings, concentration, risks, catalysts, and possible actions,
but they do not connect to brokerages, place trades, rebalance accounts, or
guarantee returns.

## Completed Phases

- Phase I: Data Source and Context Layer baseline.
- Phase II: Investment Intelligence Layer.
- Phase III: First Complete Investment Committee.
- Phase IV: Committee Memory.
- Phase V, Epic 21: Specialized Investment Agents.
- Phase V, Epic 22: Committee Memory Runtime.
- Phase V, Epic 23: Portfolio Committee.

## Completed ADRs

- `docs/adr/ADR-001-market-data-provider-pattern.md`
- `docs/adr/ADR-002-unified-data-source-architecture.md`
- `docs/architecture/ADR-003-investment-intelligence-pattern.md`
- `docs/architecture/ADR-004-agent-first-committee-architecture.md`

## Completed Epic 23 Stories

- Epic 23.1: Portfolio Domain Models.
- Epic 23.2: Portfolio Provider Interface.
- Epic 23.3: Mock Portfolio Provider.
- Epic 23.4: Portfolio Service.
- Epic 23.5: Portfolio Context Provider.
- Epic 23.6: Portfolio Committee Agents.
- Epic 23.7: Portfolio Committee Orchestrator.
- Epic 23.8: CLI Portfolio Committee Runner.

## Portfolio Intelligence Architecture Flow

The completed Portfolio Intelligence flow is:

```text
Portfolio Domain
  -> Portfolio Provider
  -> Mock Portfolio Provider
  -> Portfolio Service
  -> Portfolio Context Provider
  -> Portfolio Committee Agents
  -> Portfolio Committee Orchestrator
  -> CLI Runner
```

The flow keeps concrete account data access at the provider boundary, portfolio
normalization inside domain and service layers, prompt-facing context inside the
context provider, and advisory reasoning inside committee agents and the
orchestrator.

## Key Boundaries

- Advisory only.
- No trade execution.
- No brokerage API.
- No Robinhood integration yet.
- No automatic rebalancing.
- No guaranteed returns.
- No hard-coded API keys.
- SQLite remains the v1 persistence target.
- Mock portfolio data remains deterministic and first-class for local
  development and tests.
- Portfolio committee output remains research-oriented and must preserve the
  recommendation contract: action, confidence, horizon, evidence, risks, and
  catalysts.

## Non-Goals

- Do not implement automatic trading.
- Do not place orders or generate executable trade instructions.
- Do not integrate with Robinhood or another brokerage in this milestone.
- Do not add account linking, credential storage, or brokerage authentication.
- Do not add automatic rebalancing.
- Do not add a scheduler, daemon, or production monitoring loop.
- Do not claim guaranteed returns, risk-free outcomes, or personalized
  financial advice beyond advisory research output.

## Known Follow-Up Notes

- Future real brokerage provider.
- Future multi-account support.
- Future FX normalization.
- Future watchlist intelligence.
- Future recommendation engine.
- Future execution layer as a separate architecture decision.

## Next Phase: Epic 24 - Watchlist Intelligence

Epic 24 should extend the memory-first committee architecture from owned
portfolio holdings to watched opportunities. Watchlist intelligence should
reuse existing boundaries where possible:

- provider-neutral watchlist domain models;
- deterministic mock watchlist data;
- service-owned watchlist orchestration;
- context-provider output for prompt-facing watchlist state;
- specialist agents that consume rendered context rather than raw providers;
- advisory-only recommendations that preserve the required recommendation
  fields.

Epic 24 should not introduce brokerage integration, automatic trading, or
execution behavior. Any future execution layer must be handled as a separate
architecture decision after portfolio and watchlist research workflows are
stable.

## Validation Checklist

- `docs/architecture/roadmap-v4.md` exists.
- Current architecture status is documented.
- Completed phases are listed.
- Completed ADRs are listed.
- Completed Epic 23 stories are listed.
- Portfolio Intelligence architecture flow is documented in order.
- Key boundaries include advisory-only behavior and no trade execution.
- Non-goals explicitly exclude brokerage integration, Robinhood integration,
  automatic rebalancing, and guaranteed returns.
- Known follow-up notes include future brokerage provider, multi-account
  support, FX normalization, watchlist intelligence, recommendation engine, and
  separate execution-layer architecture decision.
- Next phase identifies Epic 24: Watchlist Intelligence.
- `pytest`
