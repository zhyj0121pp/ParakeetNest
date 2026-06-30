# Roadmap

ParakeetNest v1.0 is complete and frozen as the Phase I architecture baseline.
The completed milestone review is
[Architecture Milestone Review v1.0](architecture/architecture-milestone-review-v1.0.md).
The previous planning snapshot is [Roadmap v0.3](roadmap-v0.3.md).

This roadmap no longer carries the old Epic 7-10 implementation plans. SEC
filings, financial statements, valuation, and macro work are completed v1.0
architecture capabilities and are tracked in the epic index and milestone
review.

## Phase II Direction

The recommended Phase II theme is the Investment Intelligence Layer: converting
the completed evidence pipeline into higher-level interpretation while
preserving v1.0 architecture boundaries.

Suggested Phase II epics:

- Epic 11: Economic Regime Layer.
- Epic 12: Market Regime Layer.
- Epic 13: Sector Rotation Layer.
- Epic 14: Risk Signal Layer.
- Epic 15: Portfolio Intelligence Layer.

These are directional planning items, not implementation commitments. Each
epic should receive its own proposal or architecture decision before production
work begins.

## Cross-Epic Rules

- Follow the unified Data Source Layer architecture.
- Keep providers small, source-specific, and testable.
- Keep mock providers deterministic and first-class.
- Keep live providers opt-in.
- Do not hard-code API keys.
- Do not implement automatic trading.
- Use SQLite for v1 persistence.
- Preserve the memory-first committee flow.
- Every recommendation must include action, confidence, horizon, evidence,
  risks, and catalysts.
