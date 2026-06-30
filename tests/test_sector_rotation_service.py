"""Tests for the provider-neutral Sector Rotation service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.sector_rotation import (
    MockSectorRotationProvider,
    SectorIdentifier,
    SectorPerformance,
    SectorRotationClassification,
    SectorRotationService,
    SectorRotationSnapshot,
)


AS_OF_DATE = date(2026, 6, 30)


class RecordingCalculator:
    """Test double that records service orchestration."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[SectorPerformance], date | None]] = []
        self.snapshot = SectorRotationSnapshot(
            as_of_date=AS_OF_DATE,
            signals=[],
            source="recording_calculator",
        )

    def calculate(
        self,
        sector_performance: list[SectorPerformance],
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        self.calls.append((sector_performance, as_of_date))
        return self.snapshot


def test_service_orchestrates_provider_performance_into_calculator() -> None:
    """The service should depend on abstractions and delegate calculation."""
    performance = [
        SectorPerformance(
            sector=SectorIdentifier(sector_id="energy", name="Energy"),
            period_return=0.09,
            benchmark_return=0.02,
            relative_return=0.07,
            as_of_date=AS_OF_DATE,
            window_days=63,
        )
    ]
    provider = MockSectorRotationProvider(performance=performance)
    calculator = RecordingCalculator()
    service = SectorRotationService(provider, calculator=calculator)

    result = service.get_snapshot(as_of_date=AS_OF_DATE)

    assert result is calculator.snapshot
    assert provider.calls == [AS_OF_DATE]
    assert calculator.calls == [(performance, AS_OF_DATE)]


def test_service_calculates_snapshot_from_provider_performance() -> None:
    """The default calculator should turn provider evidence into a snapshot."""
    performance = [
        SectorPerformance(
            sector=SectorIdentifier(sector_id="energy", name="Energy"),
            period_return=0.09,
            benchmark_return=0.02,
            relative_return=0.07,
            as_of_date=AS_OF_DATE,
            window_days=63,
        )
    ]
    provider = MockSectorRotationProvider(performance=performance)
    service = SectorRotationService(provider)

    snapshot = service.get_snapshot(as_of_date=AS_OF_DATE)

    assert snapshot.as_of_date == AS_OF_DATE
    assert snapshot.source == "sector_rotation_calculator"
    assert len(snapshot.signals) == 1
    assert snapshot.signals[0].classification is SectorRotationClassification.LEADING


def test_service_accepts_calculator_duck_type() -> None:
    """The service should only require a calculator-shaped abstraction."""
    calculator = RecordingCalculator()
    provider = MockSectorRotationProvider(performance=[])
    service = SectorRotationService(provider, calculator=calculator)

    snapshot = service.get_snapshot(as_of_date=AS_OF_DATE)

    assert snapshot is calculator.snapshot


def test_mock_provider_returns_deterministic_provider_neutral_performance() -> None:
    """The mock provider should not require network access or vendor payloads."""
    provider = MockSectorRotationProvider()

    performance = provider.get_sector_performance(as_of_date=AS_OF_DATE)

    assert [item.as_of_date for item in performance] == [AS_OF_DATE, AS_OF_DATE]
    assert [item.sector.name for item in performance] == [
        "Technology",
        "Utilities",
    ]
    assert [item.relative_return for item in performance] == [0.0, 0.0]


def test_mock_provider_can_be_used_through_service() -> None:
    """The mock provider should feed deterministic facts through the service."""
    service = SectorRotationService(MockSectorRotationProvider())

    snapshot = service.get_snapshot(as_of_date=AS_OF_DATE)

    assert snapshot.as_of_date == AS_OF_DATE
    assert snapshot.source == "sector_rotation_calculator"
    assert [signal.classification for signal in snapshot.signals] == [
        SectorRotationClassification.NEUTRAL,
        SectorRotationClassification.NEUTRAL,
    ]
    assert [signal.sector.name for signal in snapshot.signals] == [
        "Technology",
        "Utilities",
    ]
    assert all(signal.confidence == "high" for signal in snapshot.signals)


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
