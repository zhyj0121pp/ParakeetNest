# Epic 045: FRED Macro Provider

## Goal

Epic 045 replaces mock-only macro facts with an optional FRED-backed macro data
provider while preserving the provider-neutral Macro Layer.

Mock remains the default. Committee, context, report, and regime code continue
to consume normalized `MacroIndicator`, `MacroObservation`, `MacroSeries`, and
`MacroSnapshot` models through `MacroDataService`.

## Scope

Included:

- economic indicator observations;
- latest observation lookup;
- historical observation lookup with date filters;
- provider-neutral indicator metadata from the existing macro models;
- app bootstrap selection through macro provider config.

Excluded:

- forecasting;
- economic regime classification changes;
- committee logic changes;
- trading signals;
- AI summaries.

## Configuration

Mock remains the default:

```yaml
macro:
  provider: mock
```

FRED can be selected through provider-neutral config:

```yaml
macro:
  provider: fred
  fred_api_key_env_var: FRED_API_KEY
  timeout: 10.0
```

The FRED API key is read only from the configured environment variable. The key
is not stored in `AppConfig` and is not hard-coded.

The same shape is supported by `AppConfig`:

```python
from parakeetnest.config import AppConfig

config = AppConfig(
    macro={
        "provider": "fred",
        "fred_api_key_env_var": "FRED_API_KEY",
        "timeout": 10.0,
    }
)
```

## Implementation

- `FREDMacroProvider` implements the existing `MacroDataProvider` abstraction.
- `MacroDataProviderRegistry` registers `mock` and `fred` provider factories.
- `MacroConfig` selects the provider and carries the FRED API-key environment
  variable name plus timeout.
- `create_app()` resolves the configured macro provider and passes only
  `MacroDataService` into context and regime services.
- Committee logic does not import FRED code, FRED series IDs, or transport
  details.

## Data Mapping

Initial FRED-backed indicators:

| Provider-neutral ID | FRED series | Notes |
| --- | --- | --- |
| `fed_funds_rate` | `FEDFUNDS` | Effective federal funds rate |
| `treasury_10y_yield` | `DGS10` | 10-year Treasury yield |
| `treasury_2y_yield` | `DGS2` | 2-year Treasury yield |
| `cpi_yoy` | `CPIAUCSL` | requested with FRED `units=pc1` |
| `unemployment_rate` | `UNRATE` | unemployment rate |
| `nonfarm_payrolls` | `PAYEMS` | total nonfarm payroll employment level |
| `gdp_growth` | `GDP` | requested with FRED `units=pc1` |

The provider accepts either the provider-neutral indicator ID or the FRED series
ID as lookup input, then returns provider-neutral macro models.

FRED observations map to `MacroObservation`:

- `date` -> `period`;
- numeric `value` -> `value`;
- `"."` or missing value -> `None`.

Unsupported indicator IDs return an empty provider-neutral series with
category, frequency, and unit set to `other`.

## Failure Behavior

The adapter translates provider and transport failures before they cross the
provider boundary:

- missing API key environment variable -> `MacroDataConfigurationError`;
- unknown unsupported local indicator -> empty `MacroSeries`;
- FRED API error payload -> `MacroDataHttpError`;
- empty observations -> empty `MacroSeries`;
- malformed JSON -> `MacroDataParsingError`;
- malformed observation payload -> `MacroDataParsingError`;
- timeout or network failure -> `MacroDataHttpError`;
- HTTP status failure -> `MacroDataHttpError`.

## Testing

Tests use fake FRED responses and fake transports only. Unit tests do not make
live network calls.

Coverage includes:

- mock default provider selection;
- FRED provider selection through config;
- timeout setting passthrough;
- API key lookup from environment variable name;
- FRED alias and provider-neutral ID lookup;
- date filter query parameters;
- observation mapping, including missing values;
- latest observation and snapshot behavior;
- unknown series and empty observation behavior;
- malformed JSON and malformed observation payloads;
- timeout, HTTP error, and FRED API error translation;
- app and report paths continuing to run with mock defaults.

Validation:

```bash
python -m pytest
```

## Completion Checklist

- Mock remains default.
- FRED is selected only through `macro.provider = "fred"`.
- FRED provider implements the existing `MacroDataProvider` interface.
- FRED responses are translated into existing provider-neutral macro models.
- FRED API key comes only from an environment variable.
- No unit tests make network calls.
- No forecasting, economic regime logic changes, committee logic changes, AI
  summaries, trading signals, or automatic trading were introduced.
