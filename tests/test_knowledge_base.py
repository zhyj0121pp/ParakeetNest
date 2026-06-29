"""Tests for knowledge base and thesis tracker behavior."""

from parakeetnest.committee import Chairman, InvestmentContext, InvestmentSecretary
from parakeetnest.committee.meeting import CommitteeMeeting
from parakeetnest.committee.models import CommitteeOpinion
from parakeetnest.memory import KnowledgeBase, ThesisTracker
from parakeetnest.models import ConfidenceLevel


def test_create_thesis() -> None:
    """Creating a thesis should store version one for a symbol."""
    knowledge_base = KnowledgeBase()
    tracker = ThesisTracker(knowledge_base)

    thesis = tracker.create_thesis(
        "NVDA",
        "Own if AI infrastructure demand remains durable.",
        evidence=("AI data center demand",),
        risks=("valuation risk",),
        catalysts=("new accelerator cycle",),
    )

    assert thesis.symbol == "NVDA"
    assert len(thesis.versions) == 1
    assert thesis.latest is not None
    assert thesis.latest.version == 1
    assert thesis.latest.evidence == ("AI data center demand",)


def test_update_thesis_appends_new_version() -> None:
    """Updating a thesis should append history instead of mutating it."""
    knowledge_base = KnowledgeBase()
    tracker = ThesisTracker(knowledge_base)
    tracker.create_thesis("TSLA", "Initial thesis.")

    updated = tracker.update_thesis("TSLA", "Updated thesis after new evidence.")

    assert len(updated.versions) == 2
    assert updated.versions[0].thesis == "Initial thesis."
    assert updated.versions[1].thesis == "Updated thesis after new evidence."
    assert updated.versions[1].version == 2


def test_retrieve_latest_thesis() -> None:
    """The tracker should retrieve the latest thesis by symbol."""
    tracker = ThesisTracker(KnowledgeBase())
    tracker.create_thesis("AMD", "Initial thesis.")
    tracker.update_thesis("AMD", "Latest thesis.")

    latest = tracker.latest("AMD")

    assert latest is not None
    assert latest.thesis == "Latest thesis."
    assert latest.version == 2


def test_preserve_thesis_history() -> None:
    """All thesis versions should remain available in append order."""
    tracker = ThesisTracker(KnowledgeBase())
    tracker.create_thesis("AAPL", "Version one.")
    tracker.update_thesis("AAPL", "Version two.")
    tracker.update_thesis("AAPL", "Version three.")

    history = tracker.history("AAPL")

    assert [version.version for version in history] == [1, 2, 3]
    assert [version.thesis for version in history] == [
        "Version one.",
        "Version two.",
        "Version three.",
    ]


def test_research_notes_and_lessons_are_append_only() -> None:
    """Research notes and lessons learned should append to memory."""
    knowledge_base = KnowledgeBase()

    note = knowledge_base.add_research_note(
        title="AI supply chain",
        body="Mock research note.",
        symbol="NVDA",
    )
    lesson = knowledge_base.add_lesson_learned(
        lesson="Wait for validated evidence before increasing confidence.",
        symbol="NVDA",
    )

    assert knowledge_base.list_research_notes("NVDA") == (note,)
    assert knowledge_base.list_lessons_learned("NVDA") == (lesson,)


def test_committee_remembers_before_reasoning() -> None:
    """Committee members should receive thesis and discussion memory before review."""

    class SpyMember:
        name = "Spy"
        title = "Spy Reviewer"

        def __init__(self) -> None:
            self.seen_contexts: list[InvestmentContext] = []

        def review(self, context: InvestmentContext) -> CommitteeOpinion:
            self.seen_contexts.append(context)
            return CommitteeOpinion(
                member_name=self.name,
                role=self.title,
                symbol=context.symbol,
                viewpoint="Saw memory before reasoning.",
                confidence=ConfidenceLevel.LOW,
            )

    knowledge_base = KnowledgeBase()
    tracker = ThesisTracker(knowledge_base)
    tracker.create_thesis("NVDA", "Memory thesis v1.")
    tracker.update_thesis("NVDA", "Memory thesis v2.")
    knowledge_base.record_committee_discussion("NVDA", "Prior committee discussion.")
    spies = (SpyMember(), SpyMember(), SpyMember())
    meeting = CommitteeMeeting(
        xixi=spies[0],
        dongdong=spies[1],
        yoyo=spies[2],
        chairman=Chairman(),
        secretary=InvestmentSecretary(knowledge_base=knowledge_base),
    )

    result = meeting.run("NVDA")

    assert result.context.historical_thesis == ("Memory thesis v1.", "Memory thesis v2.")
    assert result.context.historical_discussions == ("Prior committee discussion.",)
    assert all(spy.seen_contexts for spy in spies)
    assert all(
        spy.seen_contexts[0].historical_thesis == result.context.historical_thesis
        for spy in spies
    )
    assert knowledge_base.get_committee_discussions("NVDA")[-1] == (
        result.chairman_summary.rationale
    )
