"""Tests for the provider-neutral Market Breadth service."""

from __future__ import annotations

from datetime import date

import pytest

from parakeetnest.intelligence.market_breadth import (
    BreadthRegime,
    MarketBreadthService,
    MarketBreadthSnapshot,
    MockMarketBreadthProvider,
)


SNAPSHOT_DATE = date(2026, 6, 30)


class RecordingProvider:
    """Provider test double that records breadth snapshot requests."""

    def __init__(self, snapshot: MarketBreadthSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[str] = []

    def get_breadth_snapshot(self, universe: str) -> MarketBreadthSnapshot:
        self.calls.append(universe)
        return self.snapshot


class RecordingCalculator:
    """Calculator test double that records service orchestration."""

    def __init__(
        self,
        *,
        score: float = 0.87,
        regime: BreadthRegime = BreadthRegime.STRONG,
    ) -> None:
        self.score = score
        self.regime = regime
        self.score_calls: list[MarketBreadthSnapshot] = []
        self.classify_calls: list[float] = []

    def calculate_score(self, snapshot: MarketBreadthSnapshot) -> float:
        self.score_calls.append(snapshot)
        return self.score

    def classify(self, score: float) -> BreadthRegime:
        self.classify_calls.append(score)
        return self.regime


def snapshot(
    *,
    breadth_score: float = 0.12,
    breadth_regime: BreadthRegime = BreadthRegime.STRESSED,
) -> MarketBreadthSnapshot:
    """Build one provider-neutral breadth snapshot for service tests."""
    return MarketBreadthSnapshot(
        universe="sp500",
        date=SNAPSHOT_DATE,
        advancers=320,
        decliners=150,
        unchanged=30,
        new_highs=48,
        new_lows=12,
        percent_above_20d_ma=72.0,
        percent_above_50d_ma=68.0,
        percent_above_200d_ma=61.0,
        up_volume=5_200_000_000,
        down_volume=2_100_000_000,
        breadth_score=breadth_score,
        breadth_regime=breadth_regime,
        warnings=("partial volume data",),
    )


def test_provider_called_once() -> None:
    """The service should request exactly one provider snapshot."""
    provider_snapshot = snapshot()
    provider = RecordingProvider(provider_snapshot)
    service = MarketBreadthService(provider, calculator=RecordingCalculator())

    service.get_market_breadth("SP500")

    assert provider.calls == ["SP500"]


def test_calculator_used() -> None:
    """The service should delegate score and regime work to the calculator."""
    provider_snapshot = snapshot()
    provider = RecordingProvider(provider_snapshot)
    calculator = RecordingCalculator(score=0.66, regime=BreadthRegime.HEALTHY)
    service = MarketBreadthService(provider, calculator=calculator)

    service.get_market_breadth("SP500")

    assert calculator.score_calls == [provider_snapshot]
    assert calculator.classify_calls == [0.66]


def test_returned_snapshot_has_updated_score_and_regime() -> None:
    """The returned snapshot should include calculated breadth fields."""
    provider_snapshot = snapshot()
    service = MarketBreadthService(
        RecordingProvider(provider_snapshot),
        calculator=RecordingCalculator(score=0.44, regime=BreadthRegime.NEUTRAL),
    )

    result = service.get_market_breadth("SP500")

    assert result.breadth_score == 0.44
    assert result.breadth_regime is BreadthRegime.NEUTRAL
    assert result.universe == provider_snapshot.universe
    assert result.date == provider_snapshot.date
    assert result.advancers == provider_snapshot.advancers
    assert result.decliners == provider_snapshot.decliners
    assert result.warnings == provider_snapshot.warnings


def test_provider_snapshot_is_not_mutated() -> None:
    """The service should return a new snapshot and leave provider data intact."""
    provider_snapshot = snapshot(
        breadth_score=0.05,
        breadth_regime=BreadthRegime.STRESSED,
    )
    service = MarketBreadthService(
        RecordingProvider(provider_snapshot),
        calculator=RecordingCalculator(score=0.78, regime=BreadthRegime.HEALTHY),
    )

    result = service.get_market_breadth("SP500")

    assert result is not provider_snapshot
    assert provider_snapshot.breadth_score == 0.05
    assert provider_snapshot.breadth_regime is BreadthRegime.STRESSED
    assert result.breadth_score == 0.78
    assert result.breadth_regime is BreadthRegime.HEALTHY


def test_dependency_injection_works() -> None:
    """The service should accept provider and calculator duck types."""
    provider_snapshot = snapshot()
    provider = RecordingProvider(provider_snapshot)
    calculator = RecordingCalculator(score=0.31, regime=BreadthRegime.WEAK)
    service = MarketBreadthService(provider, calculator=calculator)

    result = service.get_market_breadth("NASDAQ100")

    assert provider.calls == ["NASDAQ100"]
    assert calculator.score_calls == [provider_snapshot]
    assert calculator.classify_calls == [0.31]
    assert result.breadth_score == 0.31
    assert result.breadth_regime is BreadthRegime.WEAK


def test_default_calculator_works() -> None:
    """The default calculator should score and classify provider snapshots."""
    provider_snapshot = snapshot(
        breadth_score=0.0,
        breadth_regime=BreadthRegime.UNKNOWN,
    )
    service = MarketBreadthService(MockMarketBreadthProvider(snapshot=provider_snapshot))

    result = service.get_market_breadth("SP500")

    assert result.breadth_score != provider_snapshot.breadth_score
    assert result.breadth_score == pytest.approx(0.7157949577382687)
    assert result.breadth_regime is BreadthRegime.HEALTHY


def test_market_breadth_package_exports_service() -> None:
    """The package should expose the public service boundary."""
    import parakeetnest.intelligence.market_breadth as market_breadth

    assert market_breadth.MarketBreadthService is MarketBreadthService
