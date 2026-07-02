# Epic 044: SEC EDGAR Provider

## Goal

Epic 044 replaces mock-only SEC filing facts with an optional SEC EDGAR-backed
provider while preserving the provider-neutral SEC Filing Layer.

Mock remains the default. Committee, context, and report code continue to
consume normalized `SecFiling`, `SecFilingContent`, and `SecFilingQuery` models.

## Scope

Included:

- Company ticker to CIK lookup
- Recent filing lookup
- Filing metadata normalization
- Filing index and primary document URLs

Excluded:

- Full filing parsing
- XBRL extraction
- Financial statement extraction
- AI summaries
- Committee logic changes
- Trading or autonomous action APIs

## Configuration

Mock remains the default:

```yaml
sec:
  provider: mock
```

SEC EDGAR can be selected through provider-neutral config:

```yaml
sec:
  provider: edgar
  user_agent: "ParakeetNest contact@example.com"
  timeout: 10.0
```

`user_agent` is required when `provider` is `edgar`, because SEC requests must
identify the calling application. `timeout` is optional and defaults to 10
seconds.

The older `sec_filings` block and `sec_edgar` provider ID remain supported as
compatibility aliases, but new configuration should use `sec.provider = edgar`.

## Implementation

- `SECEDGARProvider` implements the existing `SecFilingProvider` abstraction.
- `SecFilingProviderRegistry` registers `mock` by default and registers
  `edgar` only when a user agent is configured.
- `create_app()` resolves the configured SEC provider and passes only
  `SecFilingService` into context providers.
- Committee logic does not import EDGAR code or SEC-specific transport details.

## Data Mapping

SEC `company_tickers.json` maps to provider-neutral ticker lookup:

- `ticker` -> normalized symbol
- `cik_str` -> zero-padded CIK
- `title` -> company name

SEC company submissions map `filings.recent` entries to `SecFiling`:

- `accessionNumber` -> `accession_number`
- `form` -> provider-neutral `FilingType`
- `filingDate` -> `filed_at`
- `reportDate` -> optional `report_date`
- `primaryDocDescription` -> `title`
- SEC Archives paths -> `filing_url` and `document_url`

Unsupported SEC form types are ignored rather than leaking SEC-specific models
outside the provider layer.

## Failure Behavior

The adapter translates SEC and transport failures into SEC Filing Layer errors:

- unknown ticker -> empty filing result
- malformed ticker or submissions payload -> `SecFilingParsingError`
- malformed JSON -> `SecFilingParsingError`
- timeout or network failure -> `SecFilingHttpError`
- HTTP status failure -> `SecFilingHttpError`
- missing full filing content support -> `ProviderError`

## Testing

Tests use fake SEC responses only. They do not make real network calls.

Coverage includes:

- mock default provider selection
- EDGAR provider selection via config
- required EDGAR user agent enforcement
- timeout configuration
- ticker to CIK resolution
- recent filing metadata mapping
- filing and document URL mapping
- unknown ticker handling
- malformed JSON and malformed submissions
- timeout and HTTP error translation
- provider boundary compatibility

Validation:

```bash
python -m pytest
```

## Completion Checklist

- Mock remains default.
- EDGAR is selected only through configuration.
- EDGAR provider implements the existing SEC provider interface.
- SEC responses are translated into existing domain models.
- No SEC-specific models were introduced outside the provider layer.
- No unit tests make network calls.
- No XBRL, financial statement extraction, AI summaries, trading, or committee
  changes were introduced.
