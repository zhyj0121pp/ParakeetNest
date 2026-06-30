"""Tests for the provider-neutral Market Breadth boundary."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.market_breadth import (
    BreadthRegime,
    MarketBreadthProvider,
    MarketBreadthSnapshot,
    MockMarketBreadthProvider,
)


AS_OF_DATE = date(2026, 6, 30)


class RecordingMarketBreadthProvider:
    """Test double that satisfies the MarketBreadthProvider protocol."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.snapshot = MarketBreadthSnapshot(
            universe="SP500",
            date=AS_OF_DATE,
            advancers=300,
            decliners=190,
            unchanged=10,
            new_highs=40,
            new_lows=16,
            percent_above_20d_ma=60,
            percent_above_50d_ma=55,
            percent_above_200d_ma=52,
            up_volume=4_000_000_000,
            down_volume=3_000_000_000,
            breadth_score=0.61,
            breadth_regime=BreadthRegime.HEALTHY,
            warnings=(),
        )

    def get_breadth_snapshot(self, universe: str) -> MarketBreadthSnapshot:
        self.calls.append(universe)
        return self.snapshot


def test_market_breadth_provider_accepts_structural_implementation() -> None:
    """Providers should satisfy the contract by shape, not inheritance."""
    provider: MarketBreadthProvider = RecordingMarketBreadthProvider()

    snapshot = provider.get_breadth_snapshot("SP500")

    assert snapshot.breadth_regime is BreadthRegime.HEALTHY
    assert provider.calls == ["SP500"]


def test_market_breadth_provider_signature_is_simple_and_provider_neutral() -> None:
    """The provider boundary should avoid vendor-specific dependencies."""
    signature = inspect.signature(MarketBreadthProvider.get_breadth_snapshot)

    assert list(signature.parameters) == ["self", "universe"]
    assert signature.return_annotation == "MarketBreadthSnapshot"


def test_market_breadth_provider_module_has_no_provider_specific_imports() -> None:
    """The provider abstraction should not import upstream concrete providers."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "sec",
        "macro",
        "valuation",
        "llm",
        "recommendation",
        "trading",
    }
    forbidden_modules = {
        "requests",
        "httpx",
        "yfinance",
        "aiohttp",
        "sqlite3",
    }

    source = inspect.getsource(
        sys.modules[MarketBreadthProvider.__module__]
    ).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: MarketBreadthProvider = RecordingMarketBreadthProvider()
    snapshot = provider.get_breadth_snapshot("SP500")

    assert isinstance(snapshot, MarketBreadthSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_mock_provider_returns_deterministic_provider_neutral_snapshot() -> None:
    """The mock provider should not require network access or vendor payloads."""
    provider = MockMarketBreadthProvider()

    snapshot = provider.get_breadth_snapshot("sp500")

    assert snapshot.universe == "SP500"
    assert snapshot.date == AS_OF_DATE
    assert snapshot.advancers == 312
    assert snapshot.decliners == 180
    assert snapshot.unchanged == 8
    assert snapshot.new_highs == 42
    assert snapshot.new_lows == 15
    assert snapshot.percent_above_20d_ma == 62.4
    assert snapshot.percent_above_50d_ma == 58.1
    assert snapshot.percent_above_200d_ma == 54.7
    assert snapshot.up_volume == 4_200_000_000.0
    assert snapshot.down_volume == 2_900_000_000.0
    assert snapshot.breadth_score == 0.64
    assert snapshot.breadth_regime is BreadthRegime.HEALTHY
    assert snapshot.warnings == ()
    assert provider.calls == ["sp500"]


def test_mock_provider_can_return_injected_snapshot() -> None:
    """Tests and local callers should be able to inject fixed breadth data."""
    injected = MarketBreadthSnapshot(
        universe="NASDAQ100",
        date=AS_OF_DATE,
        advancers=45,
        decliners=52,
        unchanged=3,
        new_highs=5,
        new_lows=10,
        percent_above_20d_ma=42,
        percent_above_50d_ma=39,
        percent_above_200d_ma=48,
        up_volume=1_100_000_000,
        down_volume=1_800_000_000,
        breadth_score=0.42,
        breadth_regime=BreadthRegime.WEAK,
        warnings=("participation is narrowing",),
    )
    provider = MockMarketBreadthProvider(snapshot=injected)

    snapshot = provider.get_breadth_snapshot("SP500")

    assert snapshot is injected
    assert provider.calls == ["SP500"]


def test_market_breadth_package_exports_provider_boundary() -> None:
    """The package should expose provider and mock provider boundaries."""
    import parakeetnest.intelligence.market_breadth as market_breadth

    assert market_breadth.MarketBreadthProvider is MarketBreadthProvider
    assert market_breadth.MockMarketBreadthProvider is MockMarketBreadthProvider
