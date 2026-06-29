"""Thesis repository skeleton."""


class ThesisRepository:
    """Persist and retrieve investment thesis history."""

    def get_current(self, symbol: str) -> dict[str, object] | None:
        """Return the current thesis placeholder for a symbol."""
        return None

    def save(self, symbol: str, thesis: dict[str, object]) -> None:
        """Accept a thesis for future persistence."""
