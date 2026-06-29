"""Committee meeting orchestration."""

from dataclasses import dataclass

from parakeetnest.committee.base import CommitteeMember
from parakeetnest.committee.chairman import Chairman
from parakeetnest.committee.dongdong import Dongdong
from parakeetnest.committee.models import CommitteeMeetingResult
from parakeetnest.committee.secretary import InvestmentSecretary
from parakeetnest.memory.knowledge_base import KnowledgeBase
from parakeetnest.committee.xixi import Xixi
from parakeetnest.committee.yoyo import Yoyo


@dataclass
class CommitteeMeeting:
    """Coordinate the remember-before-reason workflow."""

    xixi: CommitteeMember
    dongdong: CommitteeMember
    yoyo: CommitteeMember
    chairman: Chairman
    secretary: InvestmentSecretary

    @classmethod
    def default(cls, knowledge_base: KnowledgeBase | None = None) -> "CommitteeMeeting":
        """Create a deterministic mock committee meeting."""
        return cls(
            xixi=Xixi(),
            dongdong=Dongdong(),
            yoyo=Yoyo(),
            chairman=Chairman(),
            secretary=InvestmentSecretary(
                knowledge_base=knowledge_base or KnowledgeBase(),
            ),
        )

    def run(
        self,
        symbol: str,
        current_facts: tuple[str, ...] = (),
        data_quality_notes: tuple[str, ...] = (),
    ) -> CommitteeMeetingResult:
        """Run the memory-first deterministic committee workflow."""
        context = self.secretary.load_context(
            symbol=symbol,
            current_facts=current_facts,
            data_quality_notes=data_quality_notes,
        )
        opinions = (
            self.xixi.review(context),
            self.dongdong.review(context),
            self.yoyo.review(context),
        )
        chairman_summary = self.chairman.summarize(context, opinions)
        return self.secretary.record_discussion(context, opinions, chairman_summary)

    def review_symbol(self, symbol: str) -> CommitteeMeetingResult:
        """Run the deterministic committee workflow for a symbol."""
        return self.run(symbol)
