"""Append-only investment knowledge base service."""

from __future__ import annotations

from dataclasses import dataclass, field

from parakeetnest.memory.models import (
    InvestmentThesis,
    LessonLearned,
    ResearchNote,
    ThesisVersion,
)


@dataclass
class KnowledgeBase:
    """Store accumulated investment knowledge rather than raw market facts."""

    theses: dict[str, InvestmentThesis] = field(default_factory=dict)
    committee_discussions: dict[str, tuple[str, ...]] = field(default_factory=dict)
    research_notes: list[ResearchNote] = field(default_factory=list)
    lessons_learned: list[LessonLearned] = field(default_factory=list)

    def create_thesis(
        self,
        symbol: str,
        thesis: str,
        evidence: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        catalysts: tuple[str, ...] = (),
        invalidation_conditions: tuple[str, ...] = (),
        author: str = "Investment Secretary",
    ) -> InvestmentThesis:
        """Create the first thesis version for a symbol."""
        if symbol in self.theses:
            raise ValueError(f"Thesis already exists for {symbol}")
        version = ThesisVersion(
            symbol=symbol,
            version=1,
            thesis=thesis,
            evidence=evidence,
            risks=risks,
            catalysts=catalysts,
            invalidation_conditions=invalidation_conditions,
            author=author,
        )
        investment_thesis = InvestmentThesis(symbol=symbol, versions=(version,))
        self.theses[symbol] = investment_thesis
        return investment_thesis

    def append_thesis_version(
        self,
        symbol: str,
        thesis: str,
        evidence: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        catalysts: tuple[str, ...] = (),
        invalidation_conditions: tuple[str, ...] = (),
        author: str = "Investment Secretary",
    ) -> InvestmentThesis:
        """Append a new immutable thesis version for a symbol."""
        current = self.theses.get(symbol)
        if current is None:
            return self.create_thesis(
                symbol=symbol,
                thesis=thesis,
                evidence=evidence,
                risks=risks,
                catalysts=catalysts,
                invalidation_conditions=invalidation_conditions,
                author=author,
            )
        version = ThesisVersion(
            symbol=symbol,
            version=len(current.versions) + 1,
            thesis=thesis,
            evidence=evidence,
            risks=risks,
            catalysts=catalysts,
            invalidation_conditions=invalidation_conditions,
            author=author,
        )
        updated = InvestmentThesis(symbol=symbol, versions=(*current.versions, version))
        self.theses[symbol] = updated
        return updated

    def get_latest_thesis(self, symbol: str) -> ThesisVersion | None:
        """Return the latest thesis version for a symbol."""
        thesis = self.theses.get(symbol)
        return thesis.latest if thesis else None

    def get_thesis_history(self, symbol: str) -> tuple[ThesisVersion, ...]:
        """Return all thesis versions for a symbol."""
        thesis = self.theses.get(symbol)
        return thesis.versions if thesis else ()

    def record_committee_discussion(self, symbol: str, discussion: str) -> None:
        """Append a committee discussion summary for a symbol."""
        existing = self.committee_discussions.get(symbol, ())
        self.committee_discussions[symbol] = (*existing, discussion)

    def get_committee_discussions(self, symbol: str) -> tuple[str, ...]:
        """Return historical committee discussions for a symbol."""
        return self.committee_discussions.get(symbol, ())

    def add_research_note(
        self,
        title: str,
        body: str,
        symbol: str | None = None,
        source: str = "manual",
    ) -> ResearchNote:
        """Append a research note."""
        note = ResearchNote(title=title, body=body, symbol=symbol, source=source)
        self.research_notes.append(note)
        return note

    def list_research_notes(self, symbol: str | None = None) -> tuple[ResearchNote, ...]:
        """Return research notes, optionally filtered by symbol."""
        if symbol is None:
            return tuple(self.research_notes)
        return tuple(note for note in self.research_notes if note.symbol == symbol)

    def add_lesson_learned(
        self,
        lesson: str,
        symbol: str | None = None,
        source: str = "manual",
    ) -> LessonLearned:
        """Append a lesson learned."""
        learned = LessonLearned(lesson=lesson, symbol=symbol, source=source)
        self.lessons_learned.append(learned)
        return learned

    def list_lessons_learned(self, symbol: str | None = None) -> tuple[LessonLearned, ...]:
        """Return lessons learned, optionally filtered by symbol."""
        if symbol is None:
            return tuple(self.lessons_learned)
        return tuple(lesson for lesson in self.lessons_learned if lesson.symbol == symbol)

    def recall(self, symbol: str) -> tuple[dict[str, object], ...]:
        """Return structured memory records for a symbol."""
        latest = self.get_latest_thesis(symbol)
        records: list[dict[str, object]] = []
        if latest is not None:
            records.append(
                {
                    "kind": "latest_thesis",
                    "symbol": symbol,
                    "version": latest.version,
                    "thesis": latest.thesis,
                }
            )
        records.extend(
            {"kind": "committee_discussion", "symbol": symbol, "summary": discussion}
            for discussion in self.get_committee_discussions(symbol)
        )
        return tuple(records)

    def remember(self, symbol: str, note: dict[str, object]) -> None:
        """Append a generic memory note as a committee discussion."""
        self.record_committee_discussion(symbol, str(note))
