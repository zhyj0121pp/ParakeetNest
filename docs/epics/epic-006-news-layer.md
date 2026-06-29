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
- 6.3: Completed. Add provider registry, configuration, and application
  bootstrap wiring for the News Layer.
- 6.4: Add one live news adapter behind the provider abstraction.

## Current Status

6.3 completed.

## NewsService Responsibilities

- Single entry point for News Layer.
- Provider orchestration boundary.
- Future extension point for fallback, dedup, ranking, cache, and retry.

## Provider Registry

`NewsProviderRegistry` owns provider registration and lookup for the News Layer.
It keeps provider IDs stable and deterministic, rejects duplicate
registrations, and raises `ConfigurationError` for unknown provider IDs.

The registry intentionally does not implement fallback, retry, cache, ranking,
deduplication, or provider composition. Those behaviors remain future
`NewsService` responsibilities if the product needs them.

Supported provider IDs:

- `mock`: deterministic in-memory provider and default.

## Configuration

`AppConfig.news.provider` selects the active News provider. The default is
`mock`, matching the safe local-development posture used by the Market Data
Layer.

Application bootstrap creates the News provider registry, resolves the
configured provider, and passes only that provider into `NewsService`.

## Lifecycle

1. `AppConfig` normalizes News configuration.
2. Application bootstrap creates `NewsProviderRegistry`.
3. The registry registers available News providers in deterministic order.
4. Bootstrap resolves `config.news.provider`.
5. `NewsService` receives the selected provider.
6. Callers use `NewsService` without knowing provider registry details.

The News Layer is wired independently from Market Data. Epic 6.3 does not
connect News provider selection to `ContextService`.

## Future Providers

Future provider adapters can register behind the same `NewsProvider` contract,
including:

- Yahoo Finance news;
- Reuters;
- RSS feeds;
- SEC press releases;
- company investor relations feeds;
- curated financial news APIs.

Each adapter should convert source-specific payloads into provider-neutral
`NewsArticle` objects before data reaches services, context, memory, or
committee agents.

## Non-Goals

- No real news API integration yet.
- No Yahoo Finance news implementation yet.
- No ContextService integration yet.
- No fallback, retry, cache, ranking, deduplication, or provider composition.
- No API keys or credentials.
- No automatic trading.
- No broad refactors outside the News Layer.
