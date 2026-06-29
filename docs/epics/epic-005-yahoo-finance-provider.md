# Epic 005: Yahoo Finance Provider

## Motivation

Epic 005 added the first live market data provider behind the existing
`MarketDataProvider` contract. The goal was to let ParakeetNest fetch live quote
and historical bar data while preserving the architecture introduced by the
Market Data Layer.

The committee still receives normalized context. It does not know whether data
came from mock fixtures or Yahoo Finance, and it never imports provider SDKs.

The mock provider remains the safe default for tests and local development.

## Implemented Components

### YahooFinanceMarketDataProvider

`YahooFinanceMarketDataProvider` implements the same provider protocol as
`MockMarketDataProvider`:

- `supports(symbol)`;
- `get_snapshot(symbol)`;
- `get_price_history(symbol, range)`.

It also exposes `get_quote(symbol)` and `get_quotes(symbols)` as Yahoo-specific
adapter conveniences while returning provider-neutral `MarketDataSnapshot`
objects.

The provider maps Yahoo quote and history responses into ParakeetNest domain
models before data reaches `MarketDataService`, the Context Layer, or committee
prompts.

### MarketDataProviderRegistry

Provider selection lives in `MarketDataProviderRegistry`. Application bootstrap
creates the registry, registers available provider factories, resolves the
configured provider ID, and passes only the resulting `MarketDataProvider` to
`MarketDataService`.

Supported provider IDs:

- `mock`: deterministic in-memory provider and default.
- `yahoo`: optional live provider backed by `yfinance`.

Unknown provider IDs raise `ConfigurationError` with the configured name and
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
- Provider selection is centralized in `MarketDataProviderRegistry`.
- The mock provider remains the default so tests and local committee runs stay
  deterministic and network-free.
- The Yahoo provider imports `yfinance` lazily inside the adapter module.
- Provider-specific exceptions are mapped to `MarketDataError` subclasses before
  they cross the provider boundary.
- Yahoo retry behavior stays inside the Yahoo provider and applies only to
  transient provider availability failures.
- No automatic trading was introduced.
- No API keys were hard-coded.

## Public APIs

The intentional public API for Epic 005 is:

- `YahooFinanceMarketDataProvider`;
- `MarketDataProviderRegistry`;
- `create_market_data_provider_registry()`;
- `MarketDataConfig(provider=...)`;
- `MarketDataService(provider)`;
- provider-neutral domain models and errors exported from
  `parakeetnest.market_data`.

`ProviderError` remains a compatibility alias for `MarketDataError`.
`ProviderCapability` remains a provider-neutral enum for capability names.

## Error Handling

Yahoo-specific failures are hidden behind the Market Data Layer error hierarchy:

- invalid, missing, unsupported, or delisted symbols become
  `InvalidSymbolError`;
- rate limit failures become `RateLimitError`;
- timeouts and temporary network failures become `ProviderUnavailableError`;
- empty or malformed payloads become `MalformedMarketDataError`;
- unexpected non-retryable provider failures become `ProviderUnavailableError`
  with `retryable=False`.

Callers should catch `MarketDataError` subclasses, not `yfinance` exceptions.

## Testing

Epic 005 is covered without live network calls:

- registry tests verify default provider selection, Yahoo selection, and
  unknown-provider configuration errors;
- provider protocol tests verify Yahoo satisfies the abstraction;
- Yahoo tests inject fake `yfinance` modules and ticker objects;
- mapping tests verify quote and history payloads become domain models;
- error tests verify provider-specific failures do not escape;
- retry tests verify transient failures retry and exhausted retries raise
  provider-neutral errors;
- architecture tests verify Yahoo Finance dependencies stay isolated to the
  Yahoo provider module.

The required validation command is:

```bash
.venv/bin/python -m pytest
```

## Future Providers

Future providers should reuse the same pattern:

- implement `MarketDataProvider`;
- register a provider factory in `create_market_data_provider_registry()`;
- map provider payloads into ParakeetNest models at the edge;
- translate provider-specific exceptions into `MarketDataError` subclasses;
- keep credentials in configuration or environment variables;
- avoid automatic trading.

Candidate providers:

- `PolygonProvider` for richer quotes and historical market data.
- `AlphaVantageProvider` for a secondary quote/history source.
- `RobinhoodProvider` only for research-oriented, account-adjacent market data.

## Completion Checklist

- Market data provider can be selected by configuration.
- Default provider is `mock`.
- `mock` and `yahoo` providers are registered centrally.
- Unknown provider IDs raise a clear configuration error.
- `MarketDataService` depends only on the provider abstraction.
- Yahoo quote and history data map to provider-neutral models.
- Yahoo provider-specific exceptions do not escape the provider boundary.
- Existing provider and context service boundaries remain intact.
- No automatic trading was introduced.
- No API keys were hard-coded.
