"""Unified Investment Intelligence Context domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from parakeetnest.intelligence.health.models import MarketHealthSnapshot
from parakeetnest.intelligence.market_breadth.models import MarketBreadthSnapshot
from parakeetnest.intelligence.momentum.models import MomentumSnapshot
from parakeetnest.intelligence.risk.models import RiskAssessment
from parakeetnest.intelligence.sector_rotation.models import SectorRotationSnapshot
from parakeetnest.intelligence.sentiment.models import MarketSentimentSnapshot
from parakeetnest.regime.models import EconomicRegimeSnapshot


@dataclass(frozen=True)
class InvestmentIntelligenceContext:
    """Committee-consumable aggregate of completed intelligence signals."""

    economic_regime: EconomicRegimeSnapshot
    sector_rotation: SectorRotationSnapshot
    risk: RiskAssessment
    breadth: MarketBreadthSnapshot
    momentum: MomentumSnapshot
    sentiment: MarketSentimentSnapshot
    health: MarketHealthSnapshot
    generated_at: datetime


__all__ = ["InvestmentIntelligenceContext"]
