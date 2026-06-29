"""Investment knowledge base skeleton."""


class KnowledgeBase:
    """Store accumulated investment knowledge rather than raw market facts."""

    def recall(self, symbol: str) -> tuple[dict[str, object], ...]:
        """Return placeholder memory records for a symbol."""
        return ()

    def remember(self, symbol: str, note: dict[str, object]) -> None:
        """Accept a note for future persistence."""
