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
- 6.4: Completed. Integrate the News Layer into the Context Layer through
  `NewsContextProvider`.
- 6.5: Completed. Add Yahoo Finance News provider behind the existing
  `NewsService` and `NewsProvider` boundaries.
- 6.6: Completed. Finalize News Layer documentation and establish the unified
  Data Source Layer architecture for future Epics.

## Current Status

Epic 6 completed.

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
- `yahoo`: optional live provider backed by Yahoo Finance through `yfinance`.

## Configuration

`AppConfig.news.provider` selects the active News provider. The default is
`mock`, matching the safe local-development posture used by the Market Data
Layer.

Application bootstrap creates the News provider registry, resolves the
configured provider, passes only that provider into `NewsService`, and injects
`NewsService` into the Context Layer's `NewsContextProvider`.

## Lifecycle

1. `AppConfig` normalizes News configuration.
2. Application bootstrap creates `NewsProviderRegistry`.
3. The registry registers available News providers in deterministic order.
4. Bootstrap resolves `config.news.provider`.
5. `NewsService` receives the selected provider.
6. Context integration uses `NewsContextProvider` with `NewsService`, not the
   provider registry.
7. Other callers use `NewsService` without knowing provider registry details.

The News Layer is wired independently from Market Data, while the Yahoo News
adapter intentionally reuses the Market Data Layer's provider-neutral error
classes and retry conventions for consistent operational behavior.

## Yahoo Finance News Provider

`YahooFinanceNewsProvider` implements the `NewsProvider` contract. It is
registered under provider ID `yahoo` and can be selected with:

```python
AppConfig(news={"provider": "yahoo"})
```

The production path remains:

1. `NewsService.get_news(...)`
2. configured `YahooFinanceNewsProvider`
3. Yahoo Finance through `yfinance`

The provider imports `yfinance` lazily and accepts an injected module in tests,
so unit tests use mocked Yahoo responses and never require network access.

## Data Mapping

Yahoo payloads are normalized into `NewsArticle` values before they cross the
provider boundary:

- Yahoo `title` or `content.title` -> `NewsArticle.title`.
- Yahoo `link`, `url`, `canonicalUrl.url`, or `clickThroughUrl.url` ->
  `NewsArticle.url`.
- Yahoo `publisher`, `provider.displayName`, or `provider.name` ->
  `NewsArticle.source`.
- Yahoo `providerPublishTime`, `pubDate`, or `displayTime` ->
  UTC `NewsArticle.published_at`.
- Yahoo `summary` or `description` -> `NewsArticle.summary`.
- Yahoo `relatedTickers`, `symbols`, or `content.finance.stockTickers` ->
  normalized `NewsArticle.symbols`.
- The provider field is set to `yahoo`.

Empty Yahoo news responses map to an empty article list. Malformed response
shapes, missing required article fields, or invalid publication timestamps raise
provider-neutral malformed-data errors.

## Error Handling

The Yahoo News provider reuses the existing Market Data error vocabulary:

- malformed payloads raise `MalformedMarketDataError`;
- transient Yahoo, network, timeout, or service failures raise retryable
  `ProviderUnavailableError`;
- rate-limit failures raise `RateLimitError`;
- unexpected provider exceptions are wrapped and do not escape the provider
  boundary.

No `yfinance` exception type is exposed to `NewsService`, the Context Layer, or
Committee logic.

## Retry Strategy

Retry behavior matches the Yahoo Market Data provider:

- default maximum attempts: 3;
- default delay between retryable attempts: 0.1 seconds;
- `MarketDataError` subclasses are not retried;
- transient provider failures are retried until success or exhaustion;
- exhausted retries raise the provider-neutral mapped error.

Tests inject `max_attempts` and `retry_delay_seconds=0` to verify retry success
and exhaustion deterministically.

## Context Integration

Epic 6.4 adds `NewsContext` to the Context Layer and registers a
provider-agnostic `NewsContextProvider` during application bootstrap.

`ContextService` receives the news section only from registered context
providers. It does not import or access `NewsProviderRegistry`; provider
selection remains isolated to application bootstrap and the News Layer service
boundary.

## Data Flow

1. Committee workflow asks `ContextService` to build a `MeetingContext`.
2. `ContextService` invokes enabled context providers in configured order.
3. `NewsContextProvider` converts the `ContextRequest` symbols into a
   `NewsQuery`.
4. `NewsContextProvider` calls `NewsService.get_news(...)`.
5. `NewsService` delegates to the configured `NewsProvider`.
6. `NewsContextProvider` maps provider-neutral `NewsArticle` objects into
   `NewsContext` items.
7. `ContextService` merges `NewsContext` into `MeetingContext.news`.

## Layer Responsibilities

- `ContextService`: orchestrates context providers and merges partial context;
  it has no News provider registry dependency.
- `NewsContextProvider`: adapts Context Layer requests to `NewsService` and
  maps `NewsArticle` values into `NewsContext`.
- `NewsService`: single News Layer service boundary and only entry point used by
  the Context Layer for news.
- `NewsProvider`: provider-specific retrieval behind the News Layer contract.
- `NewsProviderRegistry`: bootstrap-only provider lookup by configured provider
  ID.

## Future Providers

Future provider adapters can register behind the same `NewsProvider` contract,
including:

- Reuters;
- RSS feeds;
- SEC press releases;
- company investor relations feeds;
- curated financial news APIs.

Each adapter should convert source-specific payloads into provider-neutral
`NewsArticle` objects before data reaches services, context, memory, or
committee agents.

## Non-Goals

- No service-level fallback, cache, ranking, deduplication, or provider
  composition.
- No API keys or credentials.
- No automatic trading.
- No broad refactors outside the News Layer.
