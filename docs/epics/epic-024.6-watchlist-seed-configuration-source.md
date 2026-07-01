# Epic 024.6: Watchlist Seed Configuration Source

## Goal

Allow local development watchlist items to be loaded from a simple configuration
source while keeping the watchlist repository provider-neutral and in-memory for
v1.

## Scope

This epic adds an optional app configuration field:

```python
watchlist_seed_path: Path | None
```

When provided, application bootstrap loads watchlist items from the local JSON
file and initializes `InMemoryWatchlistRepository` with those items. When omitted,
the existing empty repository behavior is preserved.

The local CLI also accepts:

```bash
parakeetnest watchlist review --watchlist-seed path/to/watchlist.json
```

## Seed Format

The seed file is a JSON array of watchlist item objects:

```json
[
  {
    "symbol": "NVDA",
    "company_name": "NVIDIA",
    "theme": "AI infrastructure",
    "reason": "Track AI accelerator demand",
    "priority": "high",
    "notes": ["Watch valuation risk"]
  }
]
```

Missing optional fields use `WatchlistItem` defaults. Symbols, notes, priority,
and status continue to normalize through the domain model.

## Boundary Decisions

- No database persistence is introduced for watchlist items.
- No brokerage integration, trade execution, or automatic trading is introduced.
- No market or news provider behavior is changed.
- No LLM calls are introduced.
- No committee runner behavior is changed.
- No add, remove, or update watchlist CLI commands are introduced.
- No ADR is introduced.

## Implementation

- Added `WatchlistSeedLoader` and `load_watchlist_items(path)`.
- Added `AppConfig.watchlist_seed_path`.
- Updated app bootstrap to seed `InMemoryWatchlistRepository` when configured.
- Added `--watchlist-seed` to `parakeetnest watchlist review`.

## Validation

Tests cover:

- loading a valid seed file;
- missing optional fields using `WatchlistItem` defaults;
- invalid JSON failing with a clear error;
- duplicate active symbols failing through repository behavior;
- application wiring loading seed items;
- CLI watchlist review rendering seeded symbols.
