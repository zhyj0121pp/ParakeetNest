"""Chairman, final committee decision maker."""

from parakeetnest.committee.models import (
    ChairmanSummary,
    CommitteeOpinion,
    InvestmentContext,
)
from parakeetnest.models import (
    ConfidenceLevel,
    InvestmentHorizon,
    Recommendation,
    RecommendationAction,
)


class Chairman:
    """Balance committee viewpoints and produce final recommendations."""

    name = "Chairman"

    def summarize(
        self,
        context: InvestmentContext | str,
        opinions: tuple[CommitteeOpinion, ...] = (),
    ) -> ChairmanSummary:
        """Create a deterministic summary without unsupported conclusions."""
        if isinstance(context, str):
            context = InvestmentContext(symbol=context)
        evidence = tuple(item for opinion in opinions for item in opinion.evidence)
        risks = tuple(dict.fromkeys(risk for opinion in opinions for risk in opinion.risks))
        catalysts = tuple(
            dict.fromkeys(catalyst for opinion in opinions for catalyst in opinion.catalysts)
        )
        confidence = ConfidenceLevel.MEDIUM if evidence else ConfidenceLevel.LOW
        return ChairmanSummary(
            symbol=context.symbol,
            action=RecommendationAction.WATCH,
            confidence=confidence,
            horizon=InvestmentHorizon.THREE_MONTHS,
            rationale=(
                "The committee reviewed memory before reasoning and will watch "
                "until more validated evidence supports a stronger action."
            ),
            evidence=evidence,
            risks=risks or ("Insufficient validated evidence.",),
            catalysts=catalysts,
            data_confidence=confidence,
        )

    def summarize_symbol(self, symbol: str) -> Recommendation:
        """Create a legacy placeholder recommendation for compatibility."""
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
