"""Committee meeting orchestration."""

from dataclasses import dataclass

from parakeetnest.committee.chairman import Chairman
from parakeetnest.committee.dongdong import Dongdong
from parakeetnest.committee.secretary import InvestmentSecretary
from parakeetnest.committee.xixi import Xixi
from parakeetnest.committee.yoyo import Yoyo
from parakeetnest.models import CommitteeMemo, Recommendation


@dataclass
class CommitteeMeeting:
    """Coordinate the remember-before-reason workflow."""

    xixi: Xixi
    dongdong: Dongdong
    yoyo: Yoyo
    chairman: Chairman
    secretary: InvestmentSecretary

    def review_symbol(self, symbol: str) -> tuple[tuple[CommitteeMemo, ...], Recommendation]:
        """Run placeholder committee reviews for a symbol."""
        memos = (
            self.xixi.review(symbol),
            self.dongdong.review(symbol),
            self.yoyo.review(symbol),
        )
        recommendation = self.chairman.summarize(symbol)
        self.secretary.collect_memos(memos)
        self.secretary.record_recommendation(recommendation)
        return memos, recommendation
