# Epic 24.1: Watchlist Domain Models

## Goal

Create the foundational domain vocabulary for Phase VII Watchlist Intelligence.
The watchlist layer should let ParakeetNest represent tracked investment
candidates, theses, signals, and committee-ready insights before any provider,
repository, service, context provider, or CLI is introduced.

## Scope

This epic adds a new `parakeetnest.watchlist` package with immutable,
provider-neutral domain models:

- `WatchlistItem`
- `WatchlistThesis`
- `WatchlistPriority`
- `WatchlistStatus`
- `WatchlistSignal`
- `WatchlistInsight`

The models support basic normalization for symbols, optional text fields, enum
values, timestamps, and immutable tuple-backed evidence collections.

## Non-Goals

This epic intentionally does not implement:

- external market, news, brokerage, or research integrations;
- automatic trading;
- hard-coded API keys;
- database persistence;
- repositories;
- providers;
- services;
- context providers;
- CLI commands;
- LLM calls or committee orchestration.

## Architecture Notes

Watchlist domain models live in `src/parakeetnest/watchlist/` and depend only on
the Python standard library. They do not import providers, data sources, LLM
code, committee runtime code, persistence, or external APIs.

The models are frozen dataclasses with enum-backed fields. Collections are
normalized to tuples so future watchlist services, context providers, and
committee memory flows can pass them around without shared mutable state.

`WatchlistItem` represents one tracked candidate and captures symbol, optional
company metadata, watchlist rationale, priority, status, notes, and timestamps.

`WatchlistThesis` captures the current investment thesis, key drivers, risks,
optional time horizon, and optional confidence.

`WatchlistSignal` captures a provider-neutral signal that may affect attention
or priority without embedding any provider payload.

`WatchlistInsight` captures a balanced synthesis with bullish factors, bearish
factors, open questions, and an optional recommended action.

## Validation Checklist

- [x] New `parakeetnest.watchlist` package added.
- [x] Public models exported from `parakeetnest.watchlist`.
- [x] Domain models are immutable frozen dataclasses.
- [x] Domain models avoid provider, data source, LLM, committee runtime,
      persistence, and external API dependencies.
- [x] Default watchlist priority is `MEDIUM`.
- [x] Default watchlist status is `ACTIVE`.
- [x] Model construction is covered by tests.
- [x] Default and source collection safety is covered by tests.
- [x] Basic dataclass serialization is covered by tests.
