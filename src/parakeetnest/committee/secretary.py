"""Investment Secretary, keeper of committee memory."""

from parakeetnest.models import CommitteeMemo, Recommendation


class InvestmentSecretary:
    """Maintain committee memory without offering investment opinions."""

    name = "Investment Secretary"

    def collect_memos(self, memos: tuple[CommitteeMemo, ...]) -> tuple[CommitteeMemo, ...]:
        """Return meeting memos for persistence by a memory repository."""
        return memos

    def record_recommendation(self, recommendation: Recommendation) -> Recommendation:
        """Return a recommendation for persistence by a memory repository."""
        return recommendation
