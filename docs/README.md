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
- [Market Data Layer](architecture/market-data-layer.md)
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
