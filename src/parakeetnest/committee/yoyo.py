"""Yoyo, Chief Risk Officer."""

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.committee.models import CommitteeOpinion, InvestmentContext
from parakeetnest.models import ConfidenceLevel, EvidenceItem


class Yoyo(CommitteeMember):
    """Identify valuation, concentration, liquidity, earnings, and macro risks."""

    name = "Yoyo"
    title = "Chief Risk Officer"

    def review(self, context: InvestmentContext) -> CommitteeOpinion:
        """Create a deterministic risk review."""
        risk_notes = tuple(
            note for note in (*context.data_quality_notes, *context.current_facts)
            if "risk" in note.lower() or "low" in note.lower() or "missing" in note.lower()
        )
        evidence = tuple(
            EvidenceItem(summary=item, source="investment_context")
            for item in risk_notes[:2]
        )
        risks = risk_notes or ("Validate downside, valuation, and concentration before action.",)
        return CommitteeOpinion(
            member_name=self.name,
            role=self.title,
            symbol=context.symbol,
            viewpoint="Risk review prioritizes uncertainty before upside.",
            confidence=ConfidenceLevel.MEDIUM,
            evidence=evidence,
            risks=risks,
            catalysts=(),
        )
