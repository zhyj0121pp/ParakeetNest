"""Decision engine skeleton."""

from parakeetnest.models import (
    ConfidenceLevel,
    InvestmentHorizon,
    Recommendation,
    RecommendationAction,
)


class DecisionEngine:
    """Produce recommendations that respect policy and committee evidence."""

    def decide(self, symbol: str) -> Recommendation:
        """Return a conservative placeholder recommendation."""
        return Recommendation(
            symbol=symbol,
            action=RecommendationAction.WATCH,
            confidence=ConfidenceLevel.LOW,
            horizon=InvestmentHorizon.THREE_MONTHS,
            evidence=(),
            risks=("Decision engine has no validated analysis yet.",),
            catalysts=(),
        )
