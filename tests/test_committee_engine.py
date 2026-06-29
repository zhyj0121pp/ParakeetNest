"""Tests for the deterministic committee engine."""

from parakeetnest.committee import (
    Chairman,
    ChairmanSummary,
    CommitteeMeetingResult,
    CommitteeOpinion,
    Dongdong,
    InvestmentContext,
    InvestmentSecretary,
    Xixi,
    Yoyo,
)
from parakeetnest.committee.base import CommitteeMember
from parakeetnest.committee.meeting import CommitteeMeeting
from parakeetnest.models import ConfidenceLevel, RecommendationAction


def test_full_committee_workflow_remembers_before_reasoning() -> None:
    """A full meeting should load memory before deterministic role reviews."""
    secretary = InvestmentSecretary(
        thesis_memory={
            "NVDA": (
                "Own only if AI infrastructure demand remains supported by evidence.",
            )
        },
        discussion_memory={"NVDA": ("Prior discussion emphasized valuation risk.",)},
    )
    meeting = CommitteeMeeting(
        xixi=Xixi(),
        dongdong=Dongdong(),
        yoyo=Yoyo(),
        chairman=Chairman(),
        secretary=secretary,
    )

    result = meeting.run(
        "NVDA",
        current_facts=(
            "AI demand growth remains visible in mock data.",
            "Valuation risk remains elevated.",
        ),
        data_quality_notes=("validated mock data quality is medium",),
    )

    assert isinstance(result, CommitteeMeetingResult)
    assert result.recorded is True
    assert result.context.historical_thesis
    assert result.context.historical_discussions
    assert [opinion.member_name for opinion in result.opinions] == [
        "Xixi",
        "Dongdong",
        "Yoyo",
    ]
    assert result.chairman_summary.symbol == "NVDA"
    assert result.chairman_summary.action is RecommendationAction.WATCH
    assert result.chairman_summary.evidence
    assert secretary.recorded_results == [result]
    assert "NVDA" in secretary.discussion_memory


def test_committee_member_protocol_accepts_mock_member() -> None:
    """The committee engine should depend on the CommitteeMember protocol."""

    class MockMember:
        name = "Mock"
        title = "Mock Reviewer"

        def review(self, context: InvestmentContext) -> CommitteeOpinion:
            return CommitteeOpinion(
                member_name=self.name,
                role=self.title,
                symbol=context.symbol,
                viewpoint="Protocol-based deterministic review.",
                confidence=ConfidenceLevel.LOW,
            )

    member: CommitteeMember = MockMember()

    opinion = member.review(InvestmentContext(symbol="AMD"))

    assert opinion.symbol == "AMD"
    assert opinion.member_name == "Mock"


def test_chairman_summary_is_typed_and_conservative() -> None:
    """Chairman should produce a typed summary without inventing a buy thesis."""
    context = InvestmentContext(symbol="TSLA")

    summary = Chairman().summarize(context, opinions=())

    assert isinstance(summary, ChairmanSummary)
    assert summary.action is RecommendationAction.WATCH
    assert summary.confidence is ConfidenceLevel.LOW
    assert summary.risks


def test_secretary_records_without_opinion() -> None:
    """The secretary should record discussion output but not create an opinion."""
    secretary = InvestmentSecretary()
    context = secretary.load_context("AAPL", current_facts=("Validated fact.",))
    summary = Chairman().summarize(context, opinions=())

    result = secretary.record_discussion(context, opinions=(), chairman_summary=summary)

    assert result.recorded is True
    assert result.opinions == ()
    assert secretary.recorded_results == [result]
