"""Chairman, final committee decision maker."""

from parakeetnest.models import (
    ConfidenceLevel,
    InvestmentHorizon,
    Recommendation,
    RecommendationAction,
)


class Chairman:
    """Balance committee viewpoints and produce final recommendations."""

    name = "Chairman"

    def summarize(self, symbol: str) -> Recommendation:
        """Create a placeholder recommendation without unsupported conclusions."""
        return Recommendation(
            symbol=symbol,
            action=RecommendationAction.WATCH,
            confidence=ConfidenceLevel.LOW,
            horizon=InvestmentHorizon.THREE_MONTHS,
            evidence=(),
            risks=("Insufficient validated evidence.",),
            catalysts=(),
            data_confidence=ConfidenceLevel.LOW,
        )
