# Epic 006: News Layer

## Goal

Add a provider-agnostic News Layer so ParakeetNest can ingest company and market
news without exposing vendor payloads to the committee, Context Layer, or memory
systems.

## Scope

- Define provider-neutral news article and query domain models.
- Define a small news provider abstraction.
- Add a deterministic mock provider for tests and local development.
- Keep the layer independent from live news APIs in the initial story.
- Preserve Clean Architecture boundaries.

## Story Plan

- 6.1: Add initial news domain models, provider abstraction, mock provider, and
  focused tests.
- 6.2: Completed. Introduce a news service boundary as the single entry point for
  provider behavior.
- 6.3: Add Context Layer integration after the domain API stabilizes.
- 6.4: Add one live news adapter behind the provider abstraction.

## Current Status

6.2 completed.

## NewsService Responsibilities

- Single entry point for News Layer.
- Provider orchestration boundary.
- Future extension point for fallback, dedup, ranking, cache, and retry.

## Non-Goals

- No real news API integration yet.
- No Yahoo Finance news implementation yet.
- No ContextService integration yet.
- No API keys or credentials.
- No automatic trading.
- No broad refactors outside the News Layer.
