"""Service boundary for the unified Investment Intelligence Context."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Mapping, Protocol

from parakeetnest.intelligence.context.models import InvestmentIntelligenceContext
from parakeetnest.intelligence.health.models import MarketHealthSnapshot
from parakeetnest.intelligence.market_breadth.models import MarketBreadthSnapshot
from parakeetnest.intelligence.momentum.models import MomentumSnapshot
from parakeetnest.intelligence.risk.models import RiskAssessment
from parakeetnest.intelligence.sector_rotation.models import SectorRotationSnapshot
from parakeetnest.intelligence.sentiment.models import MarketSentimentSnapshot
from parakeetnest.regime.models import EconomicRegimeSnapshot


class _EconomicRegimeService(Protocol):
    def get_current_regime(
        self,
        *,
        as_of_date: date | None = None,
    ) -> EconomicRegimeSnapshot:
        """Return the current economic regime snapshot."""


class _SectorRotationService(Protocol):
    def get_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return the current sector rotation snapshot."""


class _RiskService(Protocol):
    def get_risk_assessment(
        self,
        *,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        """Return the current aggregate risk assessment."""


class _MarketBreadthService(Protocol):
    def get_market_breadth(self, universe: str) -> MarketBreadthSnapshot:
        """Return the market breadth snapshot for a universe."""


class _MomentumService(Protocol):
    def get_snapshot(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumSnapshot:
        """Return the momentum snapshot for a symbol."""


class _MarketSentimentService(Protocol):
    def get_snapshot(
        self,
        *,
        as_of: date | None = None,
    ) -> MarketSentimentSnapshot:
        """Return the current market sentiment snapshot."""


class _MarketHealthService(Protocol):
    def get_market_health(
        self,
        *,
        universe: str = "US",
        as_of: date | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MarketHealthSnapshot:
        """Return the market health snapshot for a universe."""


class InvestmentIntelligenceService:
    """Aggregate completed intelligence layers into one context object."""

    def __init__(
        self,
        economic_regime_service: _EconomicRegimeService,
        sector_rotation_service: _SectorRotationService,
        risk_service: _RiskService,
        market_breadth_service: _MarketBreadthService,
        momentum_service: _MomentumService,
        sentiment_service: _MarketSentimentService,
        health_service: _MarketHealthService,
    ) -> None:
        """Initialize with explicit intelligence service dependencies."""
        self._economic_regime_service = economic_regime_service
        self._sector_rotation_service = sector_rotation_service
        self._risk_service = risk_service
        self._market_breadth_service = market_breadth_service
        self._momentum_service = momentum_service
        self._sentiment_service = sentiment_service
        self._health_service = health_service

    def build_context(
        self,
        *,
        as_of_date: date | None = None,
        universe: str = "US",
        symbol: str = "SPY",
        health_metadata: Mapping[str, Any] | None = None,
    ) -> InvestmentIntelligenceContext:
        """Build the unified context by delegating to each signal service."""
        return InvestmentIntelligenceContext(
            economic_regime=self._economic_regime_service.get_current_regime(
                as_of_date=as_of_date,
            ),
            sector_rotation=self._sector_rotation_service.get_snapshot(
                as_of_date=as_of_date,
            ),
            risk=self._risk_service.get_risk_assessment(as_of_date=as_of_date),
            breadth=self._market_breadth_service.get_market_breadth(universe),
            momentum=self._momentum_service.get_snapshot(symbol, as_of=as_of_date),
            sentiment=self._sentiment_service.get_snapshot(as_of=as_of_date),
            health=self._health_service.get_market_health(
                universe=universe,
                as_of=as_of_date,
                metadata=health_metadata,
            ),
            generated_at=datetime.now(UTC),
        )


__all__ = ["InvestmentIntelligenceService"]
