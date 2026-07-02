# Epic 042: Yahoo Finance Provider

## Goal

Epic 042 replaces mock-only market facts with an optional Yahoo Finance market
data provider while preserving the provider-neutral Market Data Layer.

The committee, report composer, and context service continue to consume
normalized `MarketDataSnapshot` and `PriceBar` models. Yahoo-specific code stays
inside `parakeetnest.market_data.yahoo`.

## Configuration

Mock remains the default:

```yaml
market_data:
  provider: mock
```

Yahoo can be selected through provider-neutral config:

```yaml
market_data:
  provider: yahoo
  max_attempts: 3
  retry_delay_seconds: 0.1
```

The same shape is supported by `AppConfig`:

```python
from parakeetnest.config import AppConfig

config = AppConfig(
    market_data={
        "provider": "yahoo",
        "max_attempts": 2,
        "retry_delay_seconds": 0.0,
    }
)
```

`yfinance` is an optional dependency for live Yahoo usage:

```bash
pip install "parakeetnest[yahoo]"
```

## Implementation

- `YahooFinanceMarketDataProvider` implements `MarketDataProvider`.
- `MarketDataProviderRegistry` registers `mock` and `yahoo` provider factories.
- `MarketDataConfig` selects the provider and carries retry settings.
- `create_app()` resolves the configured provider and passes only
  `MarketDataService` into `MarketContextProvider`.
- Committee and report layers do not import Yahoo Finance code.

## Data Mapping

Yahoo quote payloads map to `MarketDataSnapshot`:

- ticker -> `Symbol`
- quote type -> `AssetType`
- last or regular market price -> `price`
- currency -> `currency`
- market timestamp -> UTC `datetime`
- open, high, low, previous close, and volume -> optional snapshot fields

Yahoo history rows map to `PriceBar`:

- row timestamp -> UTC `start_time`
- Open, High, Low, Close -> OHLC fields
- Volume -> optional volume

## Failure Behavior

The Yahoo adapter translates provider-specific failures into Market Data Layer
errors before they cross the provider boundary:

- blank or unsupported ticker -> `InvalidSymbolError`
- timeout or transient network failure -> `ProviderUnavailableError`
- empty Yahoo quote or history response -> `MalformedMarketDataError`
- malformed payload fields -> `MalformedMarketDataError`
- rate limiting -> `RateLimitError`

Retries apply only to transient provider availability failures.

## Testing

Tests use fake `yfinance` modules and fake ticker/history objects. Unit tests do
not make live Yahoo network calls.

Coverage includes:

- mock default provider selection
- Yahoo provider selection via config
- retry setting passthrough
- quote and history mapping into domain models
- missing ticker, timeout, empty response, malformed response, and retry failure
- app/report paths continuing to run with mock defaults
- architecture boundaries that keep Yahoo imports isolated to provider modules

Validation:

```bash
python -m pytest
```

## Completion Checklist

- Mock remains default.
- Yahoo is selected only through `market_data.provider = "yahoo"`.
- Yahoo provider implements the existing `MarketDataProvider` interface.
- No committee or report judgment logic changed.
- No automatic trading was introduced.
- No API keys were hard-coded.
