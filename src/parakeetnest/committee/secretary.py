"""Investment Secretary, keeper of committee memory."""

from dataclasses import dataclass, field

from parakeetnest.committee.models import (
    ChairmanSummary,
    CommitteeMeetingResult,
    CommitteeOpinion,
    InvestmentContext,
)
from parakeetnest.memory.knowledge_base import KnowledgeBase
from parakeetnest.models import CommitteeMemo, Recommendation


@dataclass
class InvestmentSecretary:
    """Maintain committee memory without offering investment opinions."""

    name = "Investment Secretary"
    knowledge_base: KnowledgeBase = field(default_factory=KnowledgeBase)
    thesis_memory: dict[str, tuple[str, ...]] = field(default_factory=dict)
    discussion_memory: dict[str, tuple[str, ...]] = field(default_factory=dict)
    recorded_results: list[CommitteeMeetingResult] = field(default_factory=list)

    def load_context(
        self,
        symbol: str,
        current_facts: tuple[str, ...] = (),
        data_quality_notes: tuple[str, ...] = (),
    ) -> InvestmentContext:
        """Load historical thesis and discussion context before reasoning."""
        latest_thesis = self.knowledge_base.get_latest_thesis(symbol)
        thesis_history = tuple(
            version.thesis for version in self.knowledge_base.get_thesis_history(symbol)
        )
        fallback_thesis = self.thesis_memory.get(symbol, ())
        knowledge_discussions = self.knowledge_base.get_committee_discussions(symbol)
        fallback_discussions = self.discussion_memory.get(symbol, ())
        return InvestmentContext(
            symbol=symbol,
            historical_thesis=thesis_history
            or ((latest_thesis.thesis,) if latest_thesis else ())
            or fallback_thesis,
            historical_discussions=knowledge_discussions or fallback_discussions,
            current_facts=current_facts,
            data_quality_notes=data_quality_notes,
        )

    def record_discussion(
        self,
        context: InvestmentContext,
        opinions: tuple[CommitteeOpinion, ...],
        chairman_summary: ChairmanSummary,
    ) -> CommitteeMeetingResult:
        """Record a completed deterministic committee discussion."""
        result = CommitteeMeetingResult(
            context=context,
            opinions=opinions,
            chairman_summary=chairman_summary,
            recorded=True,
        )
        self.recorded_results.append(result)
        prior_discussions = self.discussion_memory.get(context.symbol, ())
        self.discussion_memory[context.symbol] = (
            *prior_discussions,
            chairman_summary.rationale,
        )
        self.knowledge_base.record_committee_discussion(
            context.symbol,
            chairman_summary.rationale,
        )
        return result

    def collect_memos(self, memos: tuple[CommitteeMemo, ...]) -> tuple[CommitteeMemo, ...]:
        """Return meeting memos for persistence by a memory repository."""
        return memos

    def record_recommendation(self, recommendation: Recommendation) -> Recommendation:
        """Return a recommendation for persistence by a memory repository."""
        return recommendation
