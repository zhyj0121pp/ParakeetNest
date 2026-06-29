# ADR 001: Market Data Provider Pattern

## Decision

ParakeetNest will use a provider registry plus a provider abstraction for market
data.

`MarketDataProviderRegistry` owns provider selection from configuration and
returns a concrete implementation of `MarketDataProvider`. `MarketDataService`
depends only on `MarketDataProvider`, not on provider-specific classes or SDKs.

Concrete providers must hide provider-specific exceptions by translating them
into `MarketDataError` subclasses before failures cross the provider boundary.

## Context

The Market Data Layer started with a deterministic mock provider and then added
Yahoo Finance as the first live provider. More providers are expected later.

Without a registry and abstraction, application bootstrap and service code would
accumulate provider-specific conditionals, vendor SDK imports, and exception
handling. That would make committee reasoning harder to keep provider-neutral
and would make future providers more invasive.

ParakeetNest must also remain research-only. The market data pattern should
support reading data, not automatic trading.

## Alternatives

One option was to instantiate providers directly in `MarketDataService`. That
would make the service responsible for provider selection and would couple it to
concrete provider modules.

Another option was to let callers choose concrete providers directly. That
would leak provider choices into context providers and application flows.

A third option was to let provider SDK exceptions escape. That would force
callers to understand `yfinance`, network, pandas, and future SDK failure modes.

## Consequences

Provider selection is centralized in `MarketDataProviderRegistry`, and unknown
provider IDs fail as configuration errors.

`MarketDataService` can stay stable while providers are added or replaced. It
performs provider-neutral orchestration and delegates data retrieval through the
protocol.

Concrete providers carry the burden of mapping vendor payloads, retrying their
own transient failures where appropriate, and converting provider-specific
exceptions into the Market Data Layer error hierarchy.

Future providers must register a factory, implement `MarketDataProvider`, avoid
hard-coded API keys, and avoid automatic trading behavior.
