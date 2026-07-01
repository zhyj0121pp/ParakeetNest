"""Deterministic mock service for the Investment Intelligence Context."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Mapping

from parakeetnest.intelligence.context.models import InvestmentIntelligenceContext
from parakeetnest.intelligence.health.models import (
    HealthComponentState,
    MarketHealthComponent,
    MarketHealthSnapshot,
    MarketHealthState,
)
from parakeetnest.intelligence.market_breadth.models import (
    BreadthRegime,
    MarketBreadthSnapshot,
)
from parakeetnest.intelligence.momentum.models import (
    MomentumRegime,
    MomentumSnapshot,
    ReversalRisk,
)
from parakeetnest.intelligence.risk.models import (
    RiskAssessment,
    RiskCategory,
    RiskLevel,
    RiskSignal,
)
from parakeetnest.intelligence.sector_rotation.models import (
    RelativeStrengthSignal,
    SectorIdentifier,
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)
from parakeetnest.intelligence.sentiment.models import (
    MarketSentimentSnapshot,
    SentimentRegime,
    SentimentSignal,
)
from parakeetnest.regime.models import (
    EconomicRegime,
    EconomicRegimeSnapshot,
    RegimeConfidence,
    RegimeIndicator,
    RegimeSignal,
)


class MockInvestmentIntelligenceService:
    """Return deterministic investment intelligence context fixtures."""

    def build_context(
        self,
        *,
        as_of_date: date | None = None,
        universe: str = "US",
        symbol: str = "SPY",
        health_metadata: Mapping[str, Any] | None = None,
    ) -> InvestmentIntelligenceContext:
        """Return a stable sample context for tests and local development."""
        observed_on = as_of_date or date(2026, 6, 30)
        normalized_universe = universe.strip().upper()
        normalized_symbol = symbol.strip().upper()
        technology = SectorIdentifier(
            sector_id="technology",
            name="Technology",
            taxonomy="standard_sector",
        )

        return InvestmentIntelligenceContext(
            economic_regime=EconomicRegimeSnapshot(
                regime=EconomicRegime.EXPANSION,
                confidence=RegimeConfidence.MEDIUM,
                as_of_date=observed_on,
                indicators=[
                    RegimeIndicator(
                        signal=RegimeSignal.GROWTH,
                        name="Real GDP growth",
                        value=2.1,
                        unit="%",
                        as_of_date=observed_on,
                        interpretation="Growth remains positive.",
                    )
                ],
                summary="Expansionary backdrop with contained inflation pressure.",
                source="mock_investment_intelligence_service",
            ),
            sector_rotation=SectorRotationSnapshot(
                as_of_date=observed_on,
                signals=[
                    SectorRotationSignal(
                        sector=technology,
                        classification=SectorRotationClassification.LEADING,
                        relative_strength=RelativeStrengthSignal(
                            sector=technology,
                            score=0.78,
                            rank=1,
                            benchmark="SPY",
                            interpretation="Technology leads the benchmark.",
                        ),
                        confidence="medium",
                        evidence=("Technology relative strength remains positive.",),
                        risks=("Leadership concentration can reverse quickly.",),
                        catalysts=("AI infrastructure demand remains a tailwind.",),
                    )
                ],
                summary="Cyclical leadership is constructive but concentrated.",
                source="mock_investment_intelligence_service",
            ),
            risk=RiskAssessment(
                overall_level=RiskLevel.MODERATE,
                overall_score=0.42,
                signals=[
                    RiskSignal(
                        category=RiskCategory.MARKET,
                        level=RiskLevel.MODERATE,
                        score=0.42,
                        label="Index volatility",
                        description="Volatility is present but not stressed.",
                        evidence=("VIX proxy remains below stress thresholds.",),
                    )
                ],
                as_of_date=observed_on,
                summary="Risk is moderate and manageable.",
                source="mock_investment_intelligence_service",
            ),
            breadth=MarketBreadthSnapshot(
                universe=normalized_universe,
                date=observed_on,
                advancers=312,
                decliners=180,
                unchanged=8,
                new_highs=42,
                new_lows=15,
                percent_above_20d_ma=62.4,
                percent_above_50d_ma=58.1,
                percent_above_200d_ma=54.7,
                up_volume=4_200_000_000,
                down_volume=2_900_000_000,
                breadth_score=0.64,
                breadth_regime=BreadthRegime.HEALTHY,
            ),
            momentum=MomentumSnapshot(
                symbol=normalized_symbol,
                as_of=observed_on,
                price_change_1m=0.043,
                price_change_3m=0.118,
                price_change_6m=0.247,
                relative_strength=82.5,
                trend_strength=0.76,
                momentum_score=0.74,
                momentum_regime=MomentumRegime.UPTREND,
                reversal_risk=ReversalRisk.MEDIUM,
                confidence=0.82,
                evidence=("Trend strength is constructive.",),
            ),
            sentiment=MarketSentimentSnapshot(
                as_of=observed_on,
                overall_score=0.57,
                confidence=0.78,
                regime=SentimentRegime.GREED,
                signals=(
                    SentimentSignal(
                        name="VIX level",
                        value=18.6,
                        normalized_score=0.61,
                        weight=0.22,
                        description="Lower volatility supports risk appetite.",
                    ),
                ),
                summary="Sentiment is constructive but not euphoric.",
            ),
            health=MarketHealthSnapshot(
                as_of=observed_on,
                universe=normalized_universe,
                health_state=MarketHealthState.HEALTHY,
                health_score=0.68,
                confidence=0.83,
                components=(
                    MarketHealthComponent(
                        name="breadth",
                        state=HealthComponentState.POSITIVE,
                        score=0.64,
                        weight=0.20,
                        evidence=("Breadth is supportive.",),
                    ),
                    MarketHealthComponent(
                        name="risk",
                        state=HealthComponentState.NEUTRAL,
                        score=0.58,
                        weight=0.20,
                        evidence=("Risk is moderate.",),
                    ),
                ),
                positives=("Trend and breadth remain supportive.",),
                negatives=("Leadership concentration deserves monitoring.",),
                warnings=("Risk is not low enough for complacency.",),
                metadata=health_metadata or {},
            ),
            generated_at=datetime(2026, 6, 30, 21, 0, tzinfo=UTC),
        )


__all__ = ["MockInvestmentIntelligenceService"]
