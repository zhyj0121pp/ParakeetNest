# Epic 24.2: Watchlist Repository / Provider Abstraction

## Goal

Add a provider-neutral repository boundary for watchlist items so future
watchlist services can depend on a small interface before persistence,
providers, committee integration, or CLI behavior exists.

## Scope

This epic adds:

- `WatchlistRepository`
- `InMemoryWatchlistRepository`

The repository supports:

- `list_items()`
- `get_item(symbol)`
- `add_item(item)`
- `update_item(item)`
- `archive_item(symbol)`

## Behavior

Symbols are normalized through `WatchlistItem` domain rules. Missing lookups
return `None`; missing updates and archives raise `ValueError`. Adding a second
active item for the same normalized symbol is rejected.

`archive_item()` marks an item as `WatchlistStatus.ARCHIVED` and keeps it in the
repository. `list_items()` returns tuple-backed results sorted by symbol so
callers receive deterministic output without access to internal mutable state.

## Architecture Notes

`InMemoryWatchlistRepository` is process-local and stores immutable
`WatchlistItem` records in a dictionary keyed by normalized symbol. It is
intended for tests and early development only.

The watchlist repository layer does not import or implement databases, file
storage, market/news/brokerage providers, LLMs, committee workflows, context
providers, services, automatic trading, or CLI commands.

## Validation Checklist

- [x] Watchlist repository contract added.
- [x] In-memory implementation added.
- [x] Symbols normalize consistently through `WatchlistItem`.
- [x] Duplicate active symbols are rejected.
- [x] Missing gets return `None`.
- [x] Missing updates fail.
- [x] Archives mark status without deleting.
- [x] Listing order is deterministic.
- [x] Returned collections do not expose mutable repository state.
