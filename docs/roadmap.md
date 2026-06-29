# Roadmap

This roadmap starts after Epic 6.6, which finalizes the News Layer and
establishes the unified Data Source Layer architecture.

Versioned roadmap documents can continue to capture specific planning snapshots
as the project evolves. The previous snapshot is [Roadmap v0.3](roadmap-v0.3.md).

## Epic 7: SEC Filing Layer

Goal: add a provider-backed SEC Filing Layer for source-attributed company
filings and fundamental documents.

Expected outcomes:

- `FilingProvider` protocol and registry.
- Provider-neutral filing metadata, document, and excerpt models.
- Deterministic mock filing provider.
- Optional live SEC provider behind configuration.
- Filing context adapter integrated into `MeetingContext.filings`.
- Tests for accession numbers, filing dates, URLs, missing data, and provider
  isolation.

## Epic 8: Macro Layer

Goal: add a provider-backed Macro Layer for economic indicators, releases, and
market regime context.

Expected outcomes:

- `MacroProvider` protocol and registry.
- Provider-neutral indicator, series, observation, and release models.
- Deterministic mock macro provider.
- Optional live provider behind configuration.
- Macro context adapter integrated into `MeetingContext.macro`.
- Tests for freshness, units, revisions, missing observations, and provider
  isolation.

## Epic 9: Portfolio Layer

Goal: add a read-only Portfolio Layer for positions, allocation, exposure, and
portfolio risk context.

Expected outcomes:

- `PortfolioProvider` protocol and registry.
- Provider-neutral account, position, allocation, and exposure models.
- Deterministic mock portfolio provider.
- Optional read-only live provider behind configuration.
- Portfolio context adapter integrated into `MeetingContext.portfolio`.
- Tests for read-only behavior, missing holdings, valuation timestamps, and
  provider isolation.

No automatic trading or order execution belongs in this Epic.

## Epic 10: Calendar Layer

Goal: add a provider-backed Calendar Layer for earnings, dividends, SEC filing
dates, macro releases, and committee scheduling context.

Expected outcomes:

- `CalendarProvider` protocol and registry.
- Provider-neutral event and calendar query models.
- Deterministic mock calendar provider.
- Optional live providers behind configuration.
- Calendar context adapter integrated into meeting context.
- Tests for time zones, event windows, duplicate events, and provider
  isolation.

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
