# Documentation

This directory contains the project documentation for ParakeetNest. It is
organized around architecture decisions, implementation epics, roadmap planning,
and lower-level design notes.

## Overview

- [Architecture](architecture/data-source-layer.md): system layers and
  boundaries that guide implementation.
- [Epics](epics/README.md): delivery history and planned work by epic.
- [Roadmap](roadmap.md): milestone-level planning for upcoming platform work.
- [ADRs](adr/README.md): architectural decision records and the template for
  future decisions.

## Architecture Docs

- [Context Layer](architecture/context-layer.md)
- [Data Source Layer](architecture/data-source-layer.md)
- [Domain Model Boundary](architecture/domain-model-boundary.md)
- [Market Data Layer](architecture/market-data-layer.md)
- [Architecture Milestone Review v1.1](architecture/architecture-milestone-review-v1.1.md)
- [Architecture Milestone Review v1.0](architecture/architecture-milestone-review-v1.0.md)
- [ADR 004: Agent-First Committee Architecture](architecture/ADR-004-agent-first-committee-architecture.md)
- [ADR 003: Investment Intelligence Layer Pattern](architecture/ADR-003-investment-intelligence-pattern.md)
- [Architecture Milestone Review v0.9](architecture/milestone-review-v0.9.md)
- [Architecture Milestone Review v0.8](architecture/milestone-review-v0.8.md)
- [Architecture Milestone Review v0.7](architecture/milestone-review-v0.7.md)
- [Architecture Milestone Review v0.6](architecture/milestone-review-v0.6.md)
- [Dependency Boundaries](dependency-boundaries.md)
- [Initial Design](design.md)

## Epic Docs

The epic index lives in [docs/epics/README.md](epics/README.md). Completed
epics have dedicated detail pages:

- [Epic 001: First AI Committee Meeting](epics/epic-001-first-committee.md)
- [Epic 002: Context Layer](epics/epic-002-context-layer.md)
- [Epic 003: Context Pipeline Refinement](epics/epic-003-context-pipeline-refinement.md)
- [Epic 004: Market Data Layer](epics/epic-004-market-data-layer.md)
- [Epic 005: Yahoo Finance Provider](epics/epic-005-yahoo-finance-provider.md)
- [Epic 006: News Layer](epics/epic-006-news-layer.md)
- [Epic 007: SEC Filing Layer](epics/epic-007-sec-filing-layer.md)
- [Epic 008: Financial Statement Layer](epics/epic-008-financial-statement-layer.md)
- [Epic 009: Valuation Layer](epics/epic-009-valuation-layer.md)
- [Epic 010: Macro Layer](epics/epic-010-macro-layer.md)
- [Epic 011: Economic Regime Layer](epics/epic-011-economic-regime.md)
- [Epic 012: Sector Rotation Layer](epics/epic-012-sector-rotation.md)

## How Docs Are Organized

- `architecture/` contains durable architecture documentation for major system
  layers.
- `epics/` contains an index of completed and planned epics, with detailed
  pages added as epics are implemented.
- `adr/` contains architectural decision records for choices that should remain
  visible over time.
- `rfc/` contains request-for-comment style proposals and freezes.
- Top-level docs such as [roadmap.md](roadmap.md), [design.md](design.md), and
  [dependency-boundaries.md](dependency-boundaries.md) capture broad project
  planning and constraints.
