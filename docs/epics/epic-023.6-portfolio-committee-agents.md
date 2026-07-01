# Epic 23.6: Portfolio Committee Agents

## Goal

Create specialized portfolio committee agents that use the existing Agent
Foundation to analyze read-only portfolio context before reasoning.

## Scope

- Add portfolio committee `AgentProfile` definitions.
- Register those profiles through the existing `AgentRegistry` mechanism.
- Add prompt sources that consume portfolio context when available.
- Keep the implementation advisory, deterministic, and testable.

## Non-Goals

- No Robinhood integration.
- No brokerage API.
- No order placement.
- No trade execution.
- No portfolio orchestration yet.
- No recommendation engine.
- No persistence changes.

## Agent List

- Portfolio Manager
- Risk Manager
- Sector Analyst
- Macro Strategist

## Agent Responsibility Summary

- Portfolio Manager: overall portfolio construction, position sizing
  observations, concentration observations, and portfolio-level tradeoff
  discussion.
- Risk Manager: downside risk, concentration risk, cash buffer, exposure
  imbalance, and drawdown awareness.
- Sector Analyst: sector allocation, industry exposure, over or under
  concentration, and thematic exposure.
- Macro Strategist: macro regime fit, rate sensitivity, liquidity environment,
  and risk-on or risk-off positioning.

## Prompt Design Notes

Each portfolio agent is defined as an immutable `AgentProfile` and can be
registered in an `InMemoryAgentRegistry` with
`register_portfolio_committee_agents`.

The agent prompt sources direct agents to review the Portfolio section first
when present and to reference:

- total equity;
- top holdings;
- sector allocation;
- risk summary;
- existing market, macro, sector rotation, regime, and investment intelligence
  context when available.

The profiles use advisory guardrails and avoid brokerage or execution behavior.
They do not change committee orchestration or persistence.

## Validation Checklist

- [x] All portfolio agents are created.
- [x] All portfolio agents have stable ids.
- [x] All portfolio agents have clear names.
- [x] All portfolio agents have portfolio-related responsibilities.
- [x] Agents can be registered in the existing registry.
- [x] Prompts mention portfolio context.
- [x] Prompts do not mention trade execution or brokerage actions.
- [x] No Robinhood, brokerage API, order placement, trade execution,
  orchestration, recommendation engine, or persistence changes were added.
