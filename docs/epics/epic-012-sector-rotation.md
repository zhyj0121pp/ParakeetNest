# Epic 012: Sector Rotation Layer

## Objective

Add a provider-neutral Sector Rotation Layer so ParakeetNest can represent
sector leadership, relative strength, momentum, and rotation state before the
AI Committee reasons over investment questions.

Epic 12.1 establishes the foundation only. It adds deterministic domain models,
a provider abstraction, a mock provider, and a service boundary. It does not add
advanced rotation algorithms, portfolio allocation, automatic trading, or
trading recommendations.

## Story 12.1: Sector Rotation Foundation

Completed. Added:

- provider-neutral sector rotation domain models;
- `SectorRotationProvider` protocol;
- deterministic `MockSectorRotationProvider`;
- `SectorRotationService`;
- network-free tests for model construction, classification values, service
  delegation, and provider-neutral behavior.

## Architecture

```text
SectorRotationProvider -> SectorRotationService -> SectorRotationSnapshot
```

This follows ADR-003's Investment Intelligence Layer Pattern. Later stories may
add classifiers, richer calculations, and context provider integration behind
the same provider-neutral boundary.

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
- `SectorRotationService`.

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

tests/
  test_sector_rotation_models.py
  test_sector_rotation_service.py
```

