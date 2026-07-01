# Epic 024: Watchlist Intelligence

Status: Completed

## Summary

Epic 24 completes the first Watchlist Intelligence slice. ParakeetNest can now
represent provider-neutral watchlist candidates, synthesize deterministic
committee-ready insights, expose those insights through the Context Layer, render
them in meeting context, review them from a local CLI command, and optionally
seed local watchlist items from JSON.

The implementation stays research-only. It does not introduce automatic trading,
brokerage integration, external watchlist providers, LLM calls, or database
persistence for watchlist items.

## Completed Sub-Epics

- [Epic 24.1: Watchlist Domain Models](epic-024.1-watchlist-domain-models.md)
- [Epic 24.2: Watchlist Repository / Provider Abstraction](epic-024.2-watchlist-repository-provider-abstraction.md)
- [Epic 24.3: Watchlist Intelligence Service](epic-024.3-watchlist-intelligence-service.md)
- [Epic 24.4: Watchlist Context Provider](epic-024.4-watchlist-context-provider.md)
- [Epic 24.5: Watchlist CLI Review Command](epic-024.5-watchlist-cli-review-command.md)
- [Epic 24.6: Watchlist Seed Configuration Source](epic-024.6-watchlist-seed-configuration-source.md)

## Final Architecture

Watchlist Intelligence follows the existing small-module, provider-neutral
pattern:

- `parakeetnest.watchlist.models` defines immutable domain models for tracked
  candidates, theses, signals, and synthesized insights.
- `parakeetnest.watchlist.repository` defines the repository boundary and an
  in-memory implementation for v1 development and tests.
- `parakeetnest.watchlist.service` builds deterministic watchlist insights from
  repository data plus optional theses and signals.
- `parakeetnest.watchlist.context_provider` adapts active insights into
  `MeetingContext.watchlist`.
- `MeetingContextPromptRenderer` renders the watchlist snapshot into
  committee-readable markdown.
- `parakeetnest.watchlist.seed` loads optional local JSON seed files into
  `WatchlistItem` instances.
- Application bootstrap wires an `InMemoryWatchlistRepository`,
  `WatchlistIntelligenceService`, and `WatchlistContextProvider`.

The committee still receives watchlist information as evidence. The watchlist
layer does not decide trades, place orders, or bypass the committee decision
flow.

## Public APIs

The `parakeetnest.watchlist` package exports:

- `WatchlistItem`
- `WatchlistThesis`
- `WatchlistPriority`
- `WatchlistStatus`
- `WatchlistSignal`
- `WatchlistInsight`
- `WatchlistRepository`
- `InMemoryWatchlistRepository`
- `normalize_watchlist_symbol`
- `WatchlistIntelligenceService`
- `WatchlistContextProvider`
- `WatchlistSeedLoader`
- `load_watchlist_items`

Key service methods:

- `WatchlistRepository.list_items()`
- `WatchlistRepository.get_item(symbol)`
- `WatchlistRepository.add_item(item)`
- `WatchlistRepository.update_item(item)`
- `WatchlistRepository.archive_item(symbol)`
- `WatchlistIntelligenceService.build_insight(symbol, theses=(), signals=())`
- `WatchlistIntelligenceService.build_all_insights(theses=(), signals=())`
- `WatchlistSeedLoader.load(path)`
- `load_watchlist_items(path)`

The application configuration now accepts:

```python
watchlist_seed_path: Path | None
```

When present, bootstrap loads the seed file into the in-memory watchlist
repository. When absent, the default watchlist remains empty.

## CLI Command

The local review command is:

```bash
parakeetnest watchlist review
```

With a local seed file:

```bash
parakeetnest watchlist review --watchlist-seed path/to/watchlist.json
```

The command builds Context Layer output using only the `watchlist` provider and
prints rendered context. It does not start committee reasoning, invoke the LLM
provider, create a committee meeting, commit database changes, or place trades.

## Seed File Format

The seed file is a JSON array. Each item is passed through `WatchlistItem`
normalization:

```json
[
  {
    "symbol": "NVDA",
    "company_name": "NVIDIA",
    "sector": "Technology",
    "theme": "AI infrastructure",
    "reason": "Track AI accelerator demand",
    "priority": "high",
    "status": "active",
    "notes": ["Watch valuation risk"]
  }
]
```

Required fields:

- `symbol`

Optional fields:

- `company_name`
- `sector`
- `theme`
- `reason`
- `priority`
- `status`
- `notes`

Missing optional fields use `WatchlistItem` defaults. Duplicate active symbols
fail through repository validation.

## Non-Goals

Epic 24 intentionally does not include:

- automatic trading or order placement;
- brokerage integration;
- hard-coded API keys;
- external market, news, or research provider behavior changes;
- database persistence for watchlist items;
- add, remove, or update watchlist CLI commands;
- LLM calls from the watchlist service or review command;
- committee runtime changes beyond context availability;
- a new ADR or architecture change.

## Validation Status

The Epic 24 implementation is covered by focused tests for:

- domain model normalization and immutability;
- repository behavior and deterministic listing;
- insight synthesis, archived item handling, and missing-input open questions;
- context provider output and rendering;
- application wiring;
- CLI parsing and watchlist review output;
- JSON seed loading and seeded CLI review.

Final documentation pass:

- [x] Epic 24.1-24.6 are documented.
- [x] Final summary document added.
- [x] Runtime behavior unchanged.
- [x] No new features added.
- [x] No architecture changes added.

## Future Work

Possible future work, outside Epic 24:

- SQLite-backed watchlist persistence.
- CRUD-oriented watchlist management commands.
- Provider-backed watchlist signals from market, news, filings, valuation, and
  sentiment layers.
- Memory writeback for watchlist events and prior watchlist decisions.
- Watchlist-triggered lightweight committee reviews.
- Portfolio-aware prioritization that compares owned positions and watched
  candidates.
- Richer thesis lifecycle tracking, including confidence and horizon history.
