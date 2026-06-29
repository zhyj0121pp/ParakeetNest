# Epic 005: Yahoo Provider

## Goals

Epic 005 adds a live market data provider behind the existing
`MarketDataProvider` contract while keeping the mock provider as the safe
default for tests and local development.

The committee still receives normalized context. It does not know whether data
came from mock fixtures or the Yahoo provider.

## Implemented Components

### YahooFinanceProvider

`YahooFinanceProvider` implements the same provider protocol as
`MockMarketDataProvider`:

- `supports(symbol)`;
- `get_snapshot(symbol)`;
- `get_price_history(symbol, range)`.

It converts vendor quote and history responses into ParakeetNest domain models
before data reaches `MarketDataService`, the Context Layer, or committee
prompts.

### MarketDataProviderRegistry

Provider selection now lives in `MarketDataProviderRegistry`. Application
bootstrap creates the registry, registers available provider factories, resolves
the configured provider ID, and passes only the resulting `MarketDataProvider`
to `MarketDataService`.

Supported provider IDs:

- `mock`: deterministic in-memory provider and default.
- `yahoo`: optional live provider.

Unknown provider IDs raise a configuration error with the configured name and
available provider IDs.

## Configuration

Default:

```yaml
market_data:
  provider: mock
```

Yahoo provider:

```yaml
market_data:
  provider: yahoo
```

The same shape can be passed to `AppConfig`:

```python
from parakeetnest.config import AppConfig

config = AppConfig(market_data={"provider": "yahoo"})
```

## Design Decisions

- `MarketDataService` public API did not change. It still depends only on
  `MarketDataProvider`.
- Provider selection is centralized in the registry. Application code should
  not add scattered provider-specific conditionals.
- The mock provider remains the default so tests and local committee runs stay
  deterministic and network-free.
- The Yahoo provider remains isolated behind its adapter module. Third-party
  SDK imports should not leak into application bootstrap, services, context
  providers, or committee code.
- No automatic trading was introduced.
- No API keys were hard-coded.

## Completion Checklist

- Market data provider can be selected by configuration.
- Default provider is `mock`.
- `mock` and `yahoo` providers are registered centrally.
- Unknown provider IDs raise a clear configuration error.
- `MarketDataService` can be constructed from the configured provider.
- Existing provider and context service boundaries remain intact.
