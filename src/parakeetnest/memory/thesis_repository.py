"""Thesis repository skeleton."""

from parakeetnest.memory.knowledge_base import KnowledgeBase


class ThesisRepository:
    """Persist and retrieve investment thesis history."""

    def __init__(self, knowledge_base: KnowledgeBase | None = None) -> None:
        """Initialize the repository with an in-memory knowledge base."""
        self.knowledge_base = knowledge_base or KnowledgeBase()

    def get_current(self, symbol: str) -> dict[str, object] | None:
        """Return the current thesis for a symbol."""
        latest = self.knowledge_base.get_latest_thesis(symbol)
        if latest is None:
            return None
        return {
            "symbol": latest.symbol,
            "version": latest.version,
            "thesis": latest.thesis,
        }

    def save(self, symbol: str, thesis: dict[str, object]) -> None:
        """Append a thesis version for future persistence."""
        self.knowledge_base.append_thesis_version(symbol, str(thesis.get("thesis", "")))
