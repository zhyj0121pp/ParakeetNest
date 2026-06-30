# Epic 012: Sector Rotation Layer

## Objective

Add a provider-neutral Sector Rotation Layer so ParakeetNest can represent
sector leadership, relative strength, momentum, and rotation state before the
AI Committee reasons over investment questions.

Epic 12.1 established the foundation. Epic 12.2 added deterministic calculation
logic. Epic 12.3 connects sector rotation into the Context Layer so committee
prompts can consume provider-neutral sector rotation evidence. The epic does not
add live market data, portfolio allocation, automatic trading, or trading
recommendations.

## Story 12.1: Sector Rotation Foundation

Completed. Added:

- provider-neutral sector rotation domain models;
- `SectorRotationProvider` protocol;
- deterministic `MockSectorRotationProvider`;
- `SectorRotationService`;
- network-free tests for model construction, classification values, service
  delegation, and provider-neutral behavior.

## Story 12.2: Sector Rotation Calculation Engine

Completed. Added deterministic relative-strength and momentum classification
inside `SectorRotationCalculator`, kept behind `SectorRotationService`.

## Story 12.3: Sector Rotation Context Integration

Completed. Added:

- `SectorRotationContextProvider`, backed by `SectorRotationService`;
- `SectorRotationContextSnapshot` and `MeetingContext.sector_rotation`;
- prompt rendering under `## Sector Rotation`;
- application bootstrap registration through `ContextProviderRegistry`;
- tests for provider support, context assembly, prompt rendering, bootstrap
  registration, and provider-neutral boundaries.

## Architecture

```text
SectorRotationProvider
  -> SectorRotationService
  -> SectorRotationSnapshot
  -> SectorRotationContextProvider
  -> MeetingContext.sector_rotation
  -> MeetingContextPromptRenderer
```

This follows ADR-003's Investment Intelligence Layer Pattern. Calculator logic
remains an internal implementation detail behind `SectorRotationService`;
application bootstrap registers only the service-backed context provider.

The layer depends conceptually on market data and economic regime context, but
it must remain provider-neutral. Market-data adapters, vendor SDKs, provider
registries, and live network calls stay outside this package.

## Public APIs

The public sector rotation package exports:

- `SectorIdentifier`;
- `SectorPerformance`;
- `RelativeStrengthSignal`;
- `MomentumSignal`;
- `SectorRotationSignal`;
- `SectorRotationSnapshot`;
- `SectorRotationClassification`;
- `SectorRotationProvider`;
- `MockSectorRotationProvider`;
- `SectorRotationService`;
- `SectorRotationContextProvider`.

`SectorRotationService` exposes:

```text
get_snapshot(as_of_date=None) -> SectorRotationSnapshot
```

## Directory Layout

```text
src/parakeetnest/intelligence/sector_rotation/
  __init__.py
  models.py
  provider.py
  service.py
  context_provider.py

tests/
  test_sector_rotation_models.py
  test_sector_rotation_service.py
  test_sector_rotation_context_provider.py
```

## Context Provider

`SectorRotationContextProvider` implements the Context Provider Pattern. It
depends on the service boundary, forwards `request.as_of` as an optional
`as_of_date`, and maps `SectorRotationSnapshot` into a prompt-facing,
provider-neutral `SectorRotationContextSnapshot`.

The context snapshot includes:

- `as_of_date`;
- `summary`;
- `leaders`;
- `improving`;
- `weakening`;
- `laggards`;
- `unknown`;
- `evidence`;
- `source`.

The provider preserves source metadata and contributes only
`MeetingContext.sector_rotation`.

## Prompt Rendering

`MeetingContextPromptRenderer` renders a dedicated `## Sector Rotation` section
with summary, sector buckets, evidence lines, source, and as-of metadata. The
renderer only formats context already prepared by the provider; it does not
calculate classifications or rotation state.

## Bootstrap

Application bootstrap creates a deterministic `SectorRotationService` using the
mock provider for v1 and registers `SectorRotationContextProvider` with
`ContextService` through `ContextProviderRegistry`. The calculator is not
exposed directly from bootstrap.
