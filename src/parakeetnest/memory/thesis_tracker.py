"""Service for managing append-only investment thesis history."""

from dataclasses import dataclass

from parakeetnest.memory.knowledge_base import KnowledgeBase
from parakeetnest.memory.models import InvestmentThesis, ThesisVersion


@dataclass
class ThesisTracker:
    """Track thesis versions without mutating historical versions."""

    knowledge_base: KnowledgeBase

    def create_thesis(
        self,
        symbol: str,
        thesis: str,
        evidence: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        catalysts: tuple[str, ...] = (),
        invalidation_conditions: tuple[str, ...] = (),
    ) -> InvestmentThesis:
        """Create the first thesis version for a symbol."""
        return self.knowledge_base.create_thesis(
            symbol=symbol,
            thesis=thesis,
            evidence=evidence,
            risks=risks,
            catalysts=catalysts,
            invalidation_conditions=invalidation_conditions,
        )

    def update_thesis(
        self,
        symbol: str,
        thesis: str,
        evidence: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        catalysts: tuple[str, ...] = (),
        invalidation_conditions: tuple[str, ...] = (),
    ) -> InvestmentThesis:
        """Append a new thesis version for a symbol."""
        return self.knowledge_base.append_thesis_version(
            symbol=symbol,
            thesis=thesis,
            evidence=evidence,
            risks=risks,
            catalysts=catalysts,
            invalidation_conditions=invalidation_conditions,
        )

    def latest(self, symbol: str) -> ThesisVersion | None:
        """Return the latest thesis version for a symbol."""
        return self.knowledge_base.get_latest_thesis(symbol)

    def history(self, symbol: str) -> tuple[ThesisVersion, ...]:
        """Return all thesis versions for a symbol."""
        return self.knowledge_base.get_thesis_history(symbol)
