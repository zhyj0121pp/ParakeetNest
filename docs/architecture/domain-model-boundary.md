# Domain Model Boundary

Status: v1.0 architecture freeze

ParakeetNest has several model families. They are intentionally separate, and
new work should keep their responsibilities clear.

## Committee Context Models

`parakeetnest.context.models` is the canonical model set for committee context.
`ContextRequest`, `MeetingContext`, `ContextMetadata`, and the context snapshot
types define what the committee receives before reasoning.

Context providers should adapt source-layer outputs into these models. The
committee should consume assembled context, not provider payloads or
source-specific service objects.

## Data-Family Domain Models

Data-family packages own their source-layer domain models:

- `parakeetnest.market_data.models`
- `parakeetnest.news.models`
- `parakeetnest.sec.models`
- `parakeetnest.financials.models`
- `parakeetnest.valuation.models`
- `parakeetnest.macro.models`

These models are canonical inside each source or derived evidence layer. They
describe provider-neutral concepts for that family and form the contract
between providers, registries, services, and context adapters.

## Legacy Collection Snapshot Boundary

`parakeetnest/domain.py` is a legacy collection snapshot boundary only. It
exists for the original collection, validation, and SQLite snapshot persistence
path.

Do not treat `parakeetnest/domain.py` as the canonical model surface for new
committee context or new data-family work. New source-layer development should
use the relevant data-family model package, then adapt into
`parakeetnest.context.models` for committee consumption.
