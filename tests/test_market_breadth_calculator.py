"""Tests for deterministic market breadth calculations."""

from __future__ import annotations

import inspect
import sys
from datetime import date

import pytest

from parakeetnest.intelligence.market_breadth import (
    BreadthRegime,
    MarketBreadthCalculator,
    MarketBreadthSnapshot,
)


AS_OF_DATE = date(2026, 6, 30)


def snapshot(
    *,
    advancers: int = 300,
    decliners: int = 200,
    new_highs: int = 40,
    new_lows: int = 20,
    percent_above_20d_ma: float = 60,
    percent_above_50d_ma: float = 55,
    percent_above_200d_ma: float = 50,
    up_volume: float = 4_000_000_000,
    down_volume: float = 2_000_000_000,
) -> MarketBreadthSnapshot:
    return MarketBreadthSnapshot(
        universe="SP500",
        date=AS_OF_DATE,
        advancers=advancers,
        decliners=decliners,
        unchanged=0,
        new_highs=new_highs,
        new_lows=new_lows,
        percent_above_20d_ma=percent_above_20d_ma,
        percent_above_50d_ma=percent_above_50d_ma,
        percent_above_200d_ma=percent_above_200d_ma,
        up_volume=up_volume,
        down_volume=down_volume,
        breadth_score=0.0,
        breadth_regime=BreadthRegime.UNKNOWN,
        warnings=(),
    )


def test_calculator_returns_raw_breadth_ratios() -> None:
    """Ratio methods should use only normalized snapshot facts."""
    calculator = MarketBreadthCalculator()
    breadth = snapshot()

    assert calculator.advance_decline_ratio(breadth) == 1.5
    assert calculator.new_high_low_ratio(breadth) == 2.0
    assert calculator.volume_ratio(breadth) == 2.0


def test_calculator_handles_divide_by_zero_denominators() -> None:
    """Zero denominators should use the required floor of one."""
    calculator = MarketBreadthCalculator()
    breadth = snapshot(
        advancers=42,
        decliners=0,
        new_highs=7,
        new_lows=0,
        up_volume=9_000_000,
        down_volume=0,
    )

    assert calculator.advance_decline_ratio(breadth) == 42
    assert calculator.new_high_low_ratio(breadth) == 7
    assert calculator.volume_ratio(breadth) == 9_000_000


def test_calculator_normalizes_moving_average_participation() -> None:
    """MA participation should average the three percent fields on a 0-1 scale."""
    calculator = MarketBreadthCalculator()
    breadth = snapshot(
        percent_above_20d_ma=90,
        percent_above_50d_ma=60,
        percent_above_200d_ma=30,
    )

    assert calculator.moving_average_participation(breadth) == pytest.approx(0.60)


def test_calculator_clamps_moving_average_participation_components() -> None:
    """Out-of-range participation inputs should not push the result outside 0-1."""
    calculator = MarketBreadthCalculator()
    breadth = snapshot(
        percent_above_20d_ma=150,
        percent_above_50d_ma=50,
        percent_above_200d_ma=-20,
    )

    assert calculator.moving_average_participation(breadth) == pytest.approx(0.50)


def test_calculator_combines_components_with_deterministic_equal_weights() -> None:
    """Score should combine A/D, highs/lows, MA participation, and volume."""
    calculator = MarketBreadthCalculator()
    breadth = snapshot(
        advancers=300,
        decliners=300,
        new_highs=30,
        new_lows=30,
        percent_above_20d_ma=50,
        percent_above_50d_ma=50,
        percent_above_200d_ma=50,
        up_volume=2_000_000,
        down_volume=2_000_000,
    )

    assert calculator.calculate_score(breadth) == pytest.approx(0.50)


def test_calculator_clamps_score_to_normalized_range() -> None:
    """Pathological negative inputs should clamp the final score."""
    calculator = MarketBreadthCalculator()
    breadth = snapshot(
        advancers=-10,
        decliners=100,
        new_highs=-5,
        new_lows=10,
        percent_above_20d_ma=-50,
        percent_above_50d_ma=-10,
        percent_above_200d_ma=-1,
        up_volume=-20,
        down_volume=100,
    )

    assert calculator.calculate_score(breadth) == 0.0


@pytest.mark.parametrize(
    ("score", "regime"),
    [
        (0.80, BreadthRegime.STRONG),
        (0.60, BreadthRegime.HEALTHY),
        (0.40, BreadthRegime.NEUTRAL),
        (0.20, BreadthRegime.WEAK),
        (0.19, BreadthRegime.STRESSED),
    ],
)
def test_calculator_classifies_regimes(score: float, regime: BreadthRegime) -> None:
    """Classification thresholds should remain stable."""
    assert MarketBreadthCalculator.classify(score) is regime


def test_calculator_classification_clamps_scores() -> None:
    """Out-of-range scores should still map to valid regimes."""
    assert MarketBreadthCalculator.classify(1.5) is BreadthRegime.STRONG
    assert MarketBreadthCalculator.classify(-0.5) is BreadthRegime.STRESSED


def test_calculator_has_no_external_dependencies() -> None:
    """The calculation layer should remain pure business logic."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "service",
        "database",
        "sqlite",
        "llm",
        "context",
        "recommendation",
        "trading",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(
        sys.modules[MarketBreadthCalculator.__module__]
    ).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    calculator = MarketBreadthCalculator()
    score = calculator.calculate_score(snapshot())

    assert 0.0 <= score <= 1.0
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_public_calculator_is_exported_from_market_breadth_package() -> None:
    """The package should expose the deterministic calculator."""
    import parakeetnest.intelligence.market_breadth as market_breadth

    assert market_breadth.MarketBreadthCalculator is MarketBreadthCalculator
