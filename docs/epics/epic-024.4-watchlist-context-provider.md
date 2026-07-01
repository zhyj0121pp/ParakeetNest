# Epic 024.4: Watchlist Context Provider

## Goal

Integrate watchlist intelligence into the Context Layer so committee meetings can
review active watchlist insights before reasoning.

## Scope

This epic adds a provider-neutral `WatchlistContextProvider` backed by
`WatchlistIntelligenceService`. The provider adapts active `WatchlistInsight`
objects into a structured `MeetingContext.watchlist` section.

The provider renders:

- symbol;
- summary;
- bullish factors;
- bearish factors;
- open questions;
- recommended action.

Archived watchlist items are excluded by default through the existing
`WatchlistIntelligenceService.build_all_insights()` behavior.

## Boundary Decisions

- No CLI is introduced.
- No LLM calls are introduced.
- No market, news, or brokerage integrations are introduced.
- No persistence is introduced; default application wiring uses an empty
  in-memory watchlist repository.
- No ADR is introduced.

## Implementation

- Added `WatchlistContextItem` and `WatchlistContextSnapshot` to the Context
  Layer models.
- Added `MeetingContext.watchlist`.
- Added `WatchlistContextProvider` in the watchlist package.
- Added watchlist prompt rendering to `MeetingContextPromptRenderer`.
- Registered the provider in application context wiring.

## Validation

Tests cover:

- provider returns context with watchlist insights;
- archived items are excluded;
- empty watchlist produces safe empty context;
- output order is deterministic;
- provider follows the existing `ContextProvider` interface;
- application wiring registers the watchlist context provider.
