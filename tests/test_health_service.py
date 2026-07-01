"""Tests for the provider-neutral Market Health service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.health import (
    HealthComponentState,
    MarketHealthCalculator,
    MarketHealthComponent,
    MarketHealthService,
    MarketHealthSnapshot,
    MarketHealthState,
    MockMarketHealthProvider,
)


AS_OF_DATE = date(2026, 6, 30)


def health_components() -> tuple[MarketHealthComponent, ...]:
    """Build one provider-neutral component set for service tests."""
    return (
        MarketHealthComponent(
            "momentum",
            HealthComponentState.POSITIVE,
            score=0.80,
            evidence=("momentum constructive",),
        ),
    )


def health_snapshot() -> MarketHealthSnapshot:
    """Build one provider-neutral market health snapshot for service tests."""
    return MarketHealthSnapshot(
        as_of=AS_OF_DATE,
        universe="US",
        health_state=MarketHealthState.ROBUST,
        health_score=0.82,
        confidence=1.0,
        components=health_components(),
        positives=("momentum: momentum constructive",),
    )


class RecordingProvider:
    """Provider test double that records component requests."""

    def __init__(self, components: tuple[MarketHealthComponent, ...]) -> None:
        self.components = components
        self.calls: list[tuple[str, date | None]] = []

    def get_market_health_components(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
    ) -> tuple[MarketHealthComponent, ...]:
        self.calls.append((universe, as_of))
        return self.components


class RecordingCalculator:
    """Calculator test double that records service orchestration."""

    def __init__(self, snapshot: MarketHealthSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[dict[str, object]] = []

    def calculate(self, **kwargs: object) -> MarketHealthSnapshot:
        self.calls.append(kwargs)
        return self.snapshot


def test_service_calls_provider() -> None:
    """The service should retrieve components from the provider."""
    components = health_components()
    provider = RecordingProvider(components)
    service = MarketHealthService(provider, RecordingCalculator(health_snapshot()))

    service.get_market_health(universe="US", as_of=AS_OF_DATE)

    assert provider.calls == [("US", AS_OF_DATE)]


def test_service_calls_calculator() -> None:
    """The service should pass provider components to the calculator."""
    components = health_components()
    calculator = RecordingCalculator(health_snapshot())
    service = MarketHealthService(RecordingProvider(components), calculator)

    service.get_market_health(universe="US", as_of=AS_OF_DATE)

    assert calculator.calls == [
        {
            "as_of": AS_OF_DATE,
            "universe": "US",
            "components": components,
            "metadata": None,
        }
    ]


def test_returned_snapshot_matches_calculator_output() -> None:
    """The service should return the exact calculator snapshot."""
    expected = health_snapshot()
    service = MarketHealthService(
        RecordingProvider(health_components()),
        RecordingCalculator(expected),
    )

    result = service.get_market_health(universe="US", as_of=AS_OF_DATE)

    assert result is expected


def test_dependency_injection_works() -> None:
    """The service should accept provider and calculator duck types."""
    components = health_components()
    expected = health_snapshot()
    provider = RecordingProvider(components)
    calculator = RecordingCalculator(expected)
    service = MarketHealthService(provider, calculator)

    result = service.get_market_health(
        universe=" global ",
        as_of=AS_OF_DATE,
        metadata={"fixture": True},
    )

    assert provider.calls == [(" global ", AS_OF_DATE)]
    assert calculator.calls[0]["metadata"] == {"fixture": True}
    assert result is expected


def test_service_requires_explicit_dependencies() -> None:
    """The public constructor should keep provider and calculator injectable."""
    signature = inspect.signature(MarketHealthService)

    assert list(signature.parameters) == ["provider", "calculator"]
    assert signature.parameters["provider"].default is inspect.Signature.empty
    assert signature.parameters["calculator"].default is inspect.Signature.empty


def test_mock_provider_works_with_real_calculator() -> None:
    """The mock provider should compose with the real calculator."""
    provider = MockMarketHealthProvider()
    service = MarketHealthService(provider, MarketHealthCalculator())

    result = service.get_market_health(as_of=AS_OF_DATE)

    assert provider.calls == [("US", AS_OF_DATE)]
    assert result == MarketHealthCalculator().calculate(
        as_of=AS_OF_DATE,
        universe="US",
        components=MockMarketHealthProvider().get_market_health_components(),
    )


def test_service_has_no_duplicated_business_logic() -> None:
    """The service should not score, classify, or generate summaries."""
    forbidden_names = {
        "calculate_score",
        "classify_health",
        "confidence_for",
        "positives_for",
        "negatives_for",
        "warnings_for",
        "health_score",
        "health_state",
    }
    source = inspect.getsource(sys.modules[MarketHealthService.__module__])

    assert all(name not in source for name in forbidden_names)


def test_health_package_exports_complete_public_api() -> None:
    """The package export list should cover the Epic 17 Health Layer surface."""
    import parakeetnest.intelligence.health as health

    assert health.__all__ == [
        "DEFAULT_WEIGHTS",
        "HealthComponentState",
        "MarketHealthCalculator",
        "MarketHealthComponent",
        "MarketHealthProvider",
        "MarketHealthService",
        "MarketHealthSnapshot",
        "MarketHealthState",
        "MockMarketHealthProvider",
    ]
