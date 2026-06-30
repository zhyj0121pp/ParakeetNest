"""Tests for the provider-neutral Sector Rotation service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.sector_rotation import (
    MockSectorRotationProvider,
    SectorIdentifier,
    SectorRotationClassification,
    SectorRotationService,
    SectorRotationSignal,
    SectorRotationSnapshot,
)


AS_OF_DATE = date(2026, 6, 30)


def test_service_delegates_snapshot_request_to_provider() -> None:
    """The service should depend on the provider abstraction."""
    snapshot = SectorRotationSnapshot(
        as_of_date=AS_OF_DATE,
        signals=[
            SectorRotationSignal(
                sector=SectorIdentifier(sector_id="energy", name="Energy"),
                classification=SectorRotationClassification.LEADING,
            )
        ],
        source="test_double",
    )
    provider = MockSectorRotationProvider(snapshot=snapshot)
    service = SectorRotationService(provider)

    result = service.get_snapshot(as_of_date=AS_OF_DATE)

    assert result is snapshot
    assert provider.calls == [AS_OF_DATE]


def test_mock_provider_returns_deterministic_provider_neutral_snapshot() -> None:
    """The mock provider should not require network access or vendor payloads."""
    provider = MockSectorRotationProvider()

    snapshot = provider.get_sector_rotation_snapshot(as_of_date=AS_OF_DATE)

    assert snapshot.as_of_date == AS_OF_DATE
    assert snapshot.source == "mock_sector_rotation_provider"
    assert [signal.classification for signal in snapshot.signals] == [
        SectorRotationClassification.NEUTRAL,
        SectorRotationClassification.NEUTRAL,
    ]
    assert [signal.sector.name for signal in snapshot.signals] == [
        "Technology",
        "Utilities",
    ]
    assert all(signal.confidence == "unknown" for signal in snapshot.signals)


def test_sector_rotation_service_is_provider_independent() -> None:
    """The service should not import provider-specific or network modules."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "llm",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[SectorRotationService.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    service = SectorRotationService(MockSectorRotationProvider())
    snapshot = service.get_snapshot(as_of_date=AS_OF_DATE)

    assert isinstance(snapshot, SectorRotationSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_sector_rotation_package_exports_service_and_provider() -> None:
    """The package should expose the service and provider boundary."""
    import parakeetnest.intelligence.sector_rotation as sector_rotation

    assert sector_rotation.SectorRotationService is SectorRotationService
    assert sector_rotation.MockSectorRotationProvider is MockSectorRotationProvider
    assert sector_rotation.SectorRotationProvider.__name__ == "SectorRotationProvider"

