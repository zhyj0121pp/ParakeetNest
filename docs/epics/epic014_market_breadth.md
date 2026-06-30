# Epic 014: Market Breadth Layer

## Purpose

Epic 14 adds a provider-neutral Market Breadth Layer to ParakeetNest v1.1. The
layer gives the committee a broad-market participation signal before it reasons
over investment questions. It captures advance/decline participation, new
high/new low participation, moving-average participation, volume participation,
and a normalized breadth regime.

The layer is read-only intelligence. It does not implement automatic trading,
portfolio execution, broker integration, or provider-specific data contracts.

## Architecture

```text
MarketBreadthProvider
        |
        v
MarketBreadthService
        |
        v
MarketBreadthCalculator
        |
        v
MarketBreadthContextProvider
        |
        v
Context Pipeline
        |
        v
AI Committee
```

The package follows the v1.1 Investment Intelligence pattern:

- providers return normalized domain snapshots;
- services own the public application boundary;
- calculators stay deterministic and network-free;
- context providers translate service results into `MeetingContext`;
- bootstrap wires a mock provider for v1.1 while keeping upper layers
  provider-neutral.

## Domain Model

The domain model lives in
`src/parakeetnest/intelligence/market_breadth/models.py`.

Public exports:

- `BreadthRegime`: provider-independent regime enum with `strong`, `healthy`,
  `neutral`, `weak`, `stressed`, and `unknown`.
- `MarketBreadthSnapshot`: immutable point-in-time breadth snapshot.

`MarketBreadthSnapshot` contains:

- `universe`;
- `date`;
- `advancers`;
- `decliners`;
- `unchanged`;
- `new_highs`;
- `new_lows`;
- `percent_above_20d_ma`;
- `percent_above_50d_ma`;
- `percent_above_200d_ma`;
- `up_volume`;
- `down_volume`;
- `breadth_score`;
- `breadth_regime`;
- `warnings`.

The model normalizes values after construction and intentionally contains no
Yahoo, mock, HTTP, credential, or vendor-specific fields.

## Provider Pattern

The provider boundary lives in
`src/parakeetnest/intelligence/market_breadth/provider.py`.

Public exports:

- `MarketBreadthProvider`;
- `MockMarketBreadthProvider`.

`MarketBreadthProvider` is a structural protocol with one method:

```text
get_breadth_snapshot(universe: str) -> MarketBreadthSnapshot
```

Provider responsibilities:

- fetch or construct breadth inputs for a requested universe;
- return a normalized `MarketBreadthSnapshot`;
- preserve provider warnings in the snapshot;
- avoid leaking provider-specific objects above the provider boundary.

`MockMarketBreadthProvider` is the v1.1 bootstrap provider. It is deterministic,
network-free, and suitable for tests and local development.

## Calculator

The calculator lives in
`src/parakeetnest/intelligence/market_breadth/calculator.py`.

Public export:

- `MarketBreadthCalculator`.

Calculator responsibilities:

- compute advance/decline ratio;
- compute new high/new low ratio;
- compute up-volume/down-volume ratio;
- compute average moving-average participation;
- calculate a normalized breadth score from provider-neutral snapshot fields;
- classify the normalized score into `BreadthRegime`.

The calculator is deterministic and has no data-provider, context-layer, or
network dependencies.

## Service

The service boundary lives in
`src/parakeetnest/intelligence/market_breadth/service.py`.

Public export:

- `MarketBreadthService`.

Service responsibilities:

- depend on `MarketBreadthProvider`, not a concrete data vendor;
- request the provider snapshot for a universe;
- run `MarketBreadthCalculator`;
- return a `MarketBreadthSnapshot` with recalculated `breadth_score` and
  `breadth_regime`;
- keep provider selection below the service boundary.

The public service method is:

```text
get_market_breadth(universe: str) -> MarketBreadthSnapshot
```

## Context Provider

The context provider lives in
`src/parakeetnest/intelligence/market_breadth/context.py`.

Public export:

- `MarketBreadthContextProvider`.

Context provider responsibilities:

- depend on a minimal service protocol with `get_market_breadth`;
- contribute `MeetingContext.market_breadth`;
- map `MarketBreadthSnapshot` into
  `parakeetnest.context.models.MarketBreadthContextSnapshot`;
- preserve warnings in `ContextMetadata`;
- support legacy plain-text context rendering for direct string requests;
- avoid calculating breadth scores or selecting providers.

The provider is registered under the `market_breadth` provider id and uses
`SP500` as its default universe.

## Bootstrap Integration

Application bootstrap wires the layer in `src/parakeetnest/app.py`:

- `_create_market_breadth_service()` creates `MarketBreadthService` with
  `MockMarketBreadthProvider` and `MarketBreadthCalculator`;
- `_create_context_provider_registry()` registers
  `MarketBreadthContextProvider(market_breadth_service)` under
  `market_breadth`;
- the `App` container exposes `market_breadth_service`.

This keeps v1.1 deterministic while allowing later provider replacement behind
the same service and context-provider boundaries.

## Public Exports

The package export file is
`src/parakeetnest/intelligence/market_breadth/__init__.py`.

All public exports are documented in this freeze:

- `BreadthRegime`;
- `MarketBreadthSnapshot`;
- `MarketBreadthProvider`;
- `MockMarketBreadthProvider`;
- `MarketBreadthCalculator`;
- `MarketBreadthService`;
- `MarketBreadthContextProvider`.

## Package Structure

The implemented package structure is:

```text
src/parakeetnest/intelligence/market_breadth/
  __init__.py
  calculator.py
  context.py
  models.py
  provider.py
  service.py
```

The test coverage for the layer is:

```text
tests/test_market_breadth_models.py
tests/test_market_breadth_provider.py
tests/test_market_breadth_calculator.py
tests/test_market_breadth_service.py
tests/test_market_breadth_context.py
```

Bootstrap integration is covered by `tests/test_app.py`.

## Testing Strategy

The Market Breadth Layer is tested with network-free unit and integration
coverage:

- model tests verify immutability, normalization, provider neutrality, and
  public exports;
- provider tests verify protocol shape, mock determinism, and provider-neutral
  imports;
- calculator tests verify ratios, normalized scoring, clamping, and regime
  classification;
- service tests verify provider delegation and recalculation of score/regime;
- context tests verify `MeetingContext.market_breadth`, warnings, metadata, and
  legacy text rendering;
- app tests verify bootstrap registration and service wiring.

Full-project verification is `pytest`.

## Future Provider Integration

A future Yahoo Market Breadth provider can replace the mock provider without
changing the calculator, service, context provider, context pipeline, or AI
committee layers.

Integration steps:

1. Add a concrete provider such as `YahooMarketBreadthProvider` that implements
   `MarketBreadthProvider`.
2. Keep Yahoo-specific request, parsing, symbol mapping, retries, and rate-limit
   handling inside that provider.
3. Convert Yahoo results into `MarketBreadthSnapshot`.
4. Preserve partial-data concerns in `warnings`.
5. Update bootstrap or configuration to pass the Yahoo provider into
   `MarketBreadthService`.

The upper-layer contract remains:

```text
MarketBreadthProvider -> MarketBreadthSnapshot
MarketBreadthService.get_market_breadth(universe)
MarketBreadthContextProvider -> MeetingContext.market_breadth
```

As long as the Yahoo provider returns a provider-neutral
`MarketBreadthSnapshot`, no upper-layer code changes are required.
