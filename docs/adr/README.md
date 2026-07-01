# Architecture Decision Records

Architecture Decision Records, or ADRs, document important technical decisions
that shape ParakeetNest over time. They preserve the reasoning behind a choice,
the alternatives considered, and the tradeoffs accepted.

## When To Create An ADR

Create an ADR when a decision affects architecture, persistence, provider
contracts, security, data flow, or long-term project direction. Small local
implementation details usually do not need ADRs unless they establish a pattern
that future work should follow.

## Records

- [ADR 001: Market Data Provider Pattern](ADR-001-market-data-provider-pattern.md)
- [ADR 002: Unified Data Source Architecture](ADR-002-unified-data-source-architecture.md)
- [ADR 003: Investment Intelligence Layer Pattern](../architecture/ADR-003-investment-intelligence-pattern.md)
- [ADR 004: Agent-First Committee Architecture](../architecture/ADR-004-agent-first-committee-architecture.md)

## ADR Template

```markdown
# ADR NNN: Title

## Decision

What decision was made?

## Context

What problem, constraint, or opportunity led to this decision?

## Alternatives

What other options were considered?

## Consequences

What tradeoffs, follow-up work, or risks come from this decision?
```
