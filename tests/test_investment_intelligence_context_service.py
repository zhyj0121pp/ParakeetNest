from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from parakeetnest.intelligence.context import (
    InvestmentIntelligenceService,
    MockInvestmentIntelligenceService,
)


class FakeEconomicRegimeService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[date | None] = []

    def get_current_regime(self, *, as_of_date: date | None = None) -> object:
        self.calls.append(as_of_date)
        return self.sample


class FakeSectorRotationService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[date | None] = []

    def get_snapshot(self, *, as_of_date: date | None = None) -> object:
        self.calls.append(as_of_date)
        return self.sample


class FakeRiskService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[date | None] = []

    def get_risk_assessment(self, *, as_of_date: date | None = None) -> object:
        self.calls.append(as_of_date)
        return self.sample


class FakeMarketBreadthService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[str] = []

    def get_market_breadth(self, universe: str) -> object:
        self.calls.append(universe)
        return self.sample


class FakeMomentumService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[tuple[str, date | None]] = []

    def get_snapshot(self, symbol: str, *, as_of: date | None = None) -> object:
        self.calls.append((symbol, as_of))
        return self.sample


class FakeSentimentService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[date | None] = []

    def get_snapshot(self, *, as_of: date | None = None) -> object:
        self.calls.append(as_of)
        return self.sample


class FakeHealthService:
    def __init__(self, sample: object) -> None:
        self.sample = sample
        self.calls: list[tuple[str, date | None, Mapping[str, Any] | None]] = []

    def get_market_health(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> object:
        self.calls.append((universe, as_of, metadata))
        return self.sample


def test_service_calls_all_seven_underlying_services_exactly_once() -> None:
    sample = MockInvestmentIntelligenceService().build_context()
    economic_regime = FakeEconomicRegimeService(sample.economic_regime)
    sector_rotation = FakeSectorRotationService(sample.sector_rotation)
    risk = FakeRiskService(sample.risk)
    breadth = FakeMarketBreadthService(sample.breadth)
    momentum = FakeMomentumService(sample.momentum)
    sentiment = FakeSentimentService(sample.sentiment)
    health = FakeHealthService(sample.health)
    service = InvestmentIntelligenceService(
        economic_regime_service=economic_regime,
        sector_rotation_service=sector_rotation,
        risk_service=risk,
        market_breadth_service=breadth,
        momentum_service=momentum,
        sentiment_service=sentiment,
        health_service=health,
    )
    observed_on = date(2026, 6, 30)
    metadata = {"source": "test"}

    context = service.build_context(
        as_of_date=observed_on,
        universe="US",
        symbol="SPY",
        health_metadata=metadata,
    )

    assert context.economic_regime is sample.economic_regime
    assert context.sector_rotation is sample.sector_rotation
    assert context.risk is sample.risk
    assert context.breadth is sample.breadth
    assert context.momentum is sample.momentum
    assert context.sentiment is sample.sentiment
    assert context.health is sample.health
    assert context.generated_at.tzinfo is not None
    assert economic_regime.calls == [observed_on]
    assert sector_rotation.calls == [observed_on]
    assert risk.calls == [observed_on]
    assert breadth.calls == ["US"]
    assert momentum.calls == [("SPY", observed_on)]
    assert sentiment.calls == [observed_on]
    assert health.calls == [("US", observed_on, metadata)]
