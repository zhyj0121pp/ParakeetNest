"""Basic tests for the initial ParakeetNest skeleton."""

from parakeetnest.committee import Chairman, Dongdong, InvestmentSecretary, Xixi, Yoyo
from parakeetnest.committee.meeting import CommitteeMeeting
from parakeetnest.database.schema import table_names
from parakeetnest.decision.engine import DecisionEngine
from parakeetnest.models import RecommendationAction


def test_decision_engine_returns_complete_placeholder_recommendation() -> None:
    """The decision engine should preserve the required recommendation shape."""
    recommendation = DecisionEngine().decide("NVDA")

    assert recommendation.symbol == "NVDA"
    assert recommendation.action is RecommendationAction.WATCH
    assert recommendation.risks
    assert recommendation.evidence == ()
    assert recommendation.catalysts == ()


def test_committee_meeting_runs_all_core_roles() -> None:
    """A meeting should collect memos from Xixi, Dongdong, and Yoyo."""
    meeting = CommitteeMeeting(
        xixi=Xixi(),
        dongdong=Dongdong(),
        yoyo=Yoyo(),
        chairman=Chairman(),
        secretary=InvestmentSecretary(),
    )

    memos, recommendation = meeting.review_symbol("TSLA")

    assert len(memos) == 3
    assert recommendation.symbol == "TSLA"


def test_database_schema_lists_v1_tables() -> None:
    """The database skeleton should expose the planned SQLite v1 tables."""
    assert "holdings" in table_names()
    assert "reports" in table_names()
