"""Xixi, Chief Fundamental Analyst."""

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.committee.models import CommitteeOpinion, InvestmentContext
from parakeetnest.models import ConfidenceLevel, EvidenceItem


class Xixi(CommitteeMember):
    """Evaluate business quality, durability, and long-term fundamentals."""

    name = "Xixi"
    title = "Chief Fundamental Analyst"

    def review(self, context: InvestmentContext) -> CommitteeOpinion:
        """Create a deterministic fundamental review."""
        evidence = tuple(
            EvidenceItem(summary=item, source="investment_context")
            for item in context.current_facts[:2]
        )
        historical_anchor = (
            " Historical thesis reviewed first."
            if context.historical_thesis
            else " No prior thesis was available."
        )
        return CommitteeOpinion(
            member_name=self.name,
            role=self.title,
            symbol=context.symbol,
            viewpoint=(
                "Business-quality review remains conservative until validated "
                f"fundamental evidence expands.{historical_anchor}"
            ),
            confidence=ConfidenceLevel.MEDIUM if evidence else ConfidenceLevel.LOW,
            evidence=evidence,
            risks=("Insufficient fundamental depth for a stronger conclusion.",),
            catalysts=(),
        )
