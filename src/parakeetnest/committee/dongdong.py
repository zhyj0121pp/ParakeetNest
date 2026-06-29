"""Dongdong, Chief Opportunity Hunter."""

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.committee.models import CommitteeOpinion, InvestmentContext
from parakeetnest.models import ConfidenceLevel, EvidenceItem


class Dongdong(CommitteeMember):
    """Search for overlooked growth opportunities and catalysts."""

    name = "Dongdong"
    title = "Chief Opportunity Hunter"

    def review(self, context: InvestmentContext) -> CommitteeOpinion:
        """Create a deterministic opportunity review."""
        catalyst_candidates = tuple(
            fact for fact in context.current_facts if "AI" in fact or "growth" in fact.lower()
        )
        evidence = tuple(
            EvidenceItem(summary=item, source="investment_context")
            for item in catalyst_candidates[:2]
        )
        catalysts = catalyst_candidates or ("Wait for clearer product or market catalysts.",)
        return CommitteeOpinion(
            member_name=self.name,
            role=self.title,
            symbol=context.symbol,
            viewpoint="Opportunity review highlights only deterministic context signals.",
            confidence=ConfidenceLevel.MEDIUM if evidence else ConfidenceLevel.LOW,
            evidence=evidence,
            risks=(),
            catalysts=catalysts,
        )
