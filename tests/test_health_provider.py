"""Tests for the provider-neutral Market Health Layer boundary."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.health import (
    HealthComponentState,
    MarketHealthComponent,
    MarketHealthProvider,
    MockMarketHealthProvider,
)


AS_OF_DATE = date(2026, 6, 30)


def sample_components() -> tuple[MarketHealthComponent, ...]:
    """Build provider-neutral component fixtures."""
    return (
        MarketHealthComponent(
            "momentum",
            HealthComponentState.POSITIVE,
            score=0.74,
            evidence=("momentum constructive",),
        ),
    )


class RecordingHealthProvider:
    """Test double that satisfies the MarketHealthProvider protocol."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, date | None]] = []
        self.components = sample_components()

    def get_market_health_components(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
    ) -> tuple[MarketHealthComponent, ...]:
        self.calls.append((universe, as_of))
        return self.components


def test_health_provider_accepts_structural_implementation() -> None:
    """Providers should satisfy the contract by shape, not inheritance."""
    provider: MarketHealthProvider = RecordingHealthProvider()

    components = provider.get_market_health_components(
        universe="US",
        as_of=AS_OF_DATE,
    )

    assert components == sample_components()
    assert provider.calls == [("US", AS_OF_DATE)]


def test_health_provider_signature_is_simple_and_provider_neutral() -> None:
    """The provider boundary should avoid vendor-specific dependencies."""
    signature = inspect.signature(MarketHealthProvider.get_market_health_components)

    assert list(signature.parameters) == ["self", "universe", "as_of"]
    assert signature.return_annotation == "tuple[MarketHealthComponent, ...]"


def test_health_provider_module_has_no_provider_specific_imports() -> None:
    """The provider abstraction should not import upstream concrete providers."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "news",
        "llm",
        "recommendation",
        "trading",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[MarketHealthProvider.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: MarketHealthProvider = RecordingHealthProvider()
    components = provider.get_market_health_components(as_of=AS_OF_DATE)

    assert components == sample_components()
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_mock_provider_returns_deterministic_components() -> None:
    """The mock provider should not require network access or vendor payloads."""
    provider = MockMarketHealthProvider()

    components = provider.get_market_health_components()

    assert tuple(component.name for component in components) == (
        "economic_regime",
        "risk",
        "breadth",
        "momentum",
        "sentiment",
        "sector_rotation",
    )
    assert tuple(component.score for component in components) == (
        0.72,
        0.40,
        0.68,
        0.74,
        0.58,
        0.55,
    )
    assert provider.calls == [("US", None)]


def test_mock_provider_multiple_calls_return_identical_results() -> None:
    """Default mock component sets should be repeatable across calls."""
    provider = MockMarketHealthProvider()

    first = provider.get_market_health_components()
    second = provider.get_market_health_components()

    assert first == second
    assert provider.calls == [("US", None), ("US", None)]


def test_mock_provider_can_return_injected_components() -> None:
    """Tests and local callers should be able to inject fixed components."""
    injected = sample_components()
    provider = MockMarketHealthProvider(components=injected)

    components = provider.get_market_health_components(
        universe="GLOBAL",
        as_of=AS_OF_DATE,
    )

    assert components is injected
    assert provider.calls == [("GLOBAL", AS_OF_DATE)]


def test_health_package_exports_provider_boundary() -> None:
    """The package should expose provider and mock provider boundaries."""
    import parakeetnest.intelligence.health as health

    assert health.MarketHealthProvider is MarketHealthProvider
    assert health.MockMarketHealthProvider is MockMarketHealthProvider
    assert "MarketHealthProvider" in health.__all__
    assert "MockMarketHealthProvider" in health.__all__
