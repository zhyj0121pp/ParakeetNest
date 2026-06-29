"""Committee discussion repository skeleton."""

from parakeetnest.models import CommitteeMemo


class DiscussionRepository:
    """Persist committee discussions and role-specific memos."""

    def list_for_symbol(self, symbol: str) -> tuple[CommitteeMemo, ...]:
        """Return placeholder discussions for a symbol."""
        return ()

    def save_many(self, memos: tuple[CommitteeMemo, ...]) -> None:
        """Accept committee memos for future persistence."""
