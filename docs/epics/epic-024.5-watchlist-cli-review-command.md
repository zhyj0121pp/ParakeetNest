# Epic 024.5: Watchlist CLI Review Command

## Goal

Add a minimal local CLI command for reviewing rendered watchlist context without
starting committee reasoning.

## Scope

This epic adds:

```bash
parakeetnest watchlist review
```

The command builds context through the existing `ContextService`, limits the
enabled Context Layer provider set to `watchlist`, and renders the resulting
`MeetingContext` with `MeetingContextPromptRenderer`.

An empty watchlist is valid. The output still includes the `## Watchlist`
section and the existing safe empty-state message.

## Boundary Decisions

- No add, remove, or update watchlist commands are introduced.
- No LLM call is introduced.
- No committee meeting is created.
- No committee runtime is invoked.
- No brokerage integration, trade execution, or order placement is introduced.
- No market or news provider behavior is changed.
- No new persistence model is introduced; the v1 app wiring continues to use the
  in-memory watchlist repository.
- No ADR is introduced.

## Implementation

- Added nested CLI parsing for `watchlist review`.
- Added `run_watchlist_review()` in the local CLI module.
- Reused application bootstrap with `enabled_context_provider_ids=("watchlist",)`.
- Reused `ContextRequest`, `ContextService`, and `MeetingContextPromptRenderer`.
- Closed application resources without committing or rolling back.

## Validation

Tests cover:

- command parsing for `watchlist review`;
- empty watchlist review succeeds;
- output includes the Watchlist section;
- the command does not invoke the LLM provider, committee runtime, or meeting
  service.
