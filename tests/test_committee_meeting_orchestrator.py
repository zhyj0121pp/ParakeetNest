"""Tests for the first persistent AI committee meeting orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from parakeetnest.committee import (
    AgentResult,
    CommitteeMeetingOrchestrator,
    MeetingContext,
    MeetingStatus,
)
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    session_scope,
)
from parakeetnest.database.models import CommitteeMeeting
from parakeetnest.llm import MockLLMProvider


def _opinion(member_name: str, role: str) -> str:
    return json.dumps(
        {
            "member_name": member_name,
            "role": role,
            "symbol": "NVDA",
            "viewpoint": f"{member_name} view.",
            "confidence": "medium",
            "evidence": [{"summary": "Test evidence.", "source": "unit_test"}],
            "risks": ["Test risk."],
            "catalysts": ["Test catalyst."],
        }
    )


def _chair_result() -> str:
    return json.dumps(
        {
            "symbol": "NVDA",
            "action": "watch",
            "confidence": "medium",
            "horizon": "3_months",
            "rationale": "Wait for confirmation.",
            "evidence": [{"summary": "Committee reviewed.", "source": "unit_test"}],
            "risks": ["Valuation risk."],
            "catalysts": ["Earnings update."],
            "data_confidence": "medium",
        }
    )


def _orchestrator(tmp_path: Path, provider: MockLLMProvider) -> CommitteeMeetingOrchestrator:
    engine = create_sqlite_engine(tmp_path / "orchestrator.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    repository = CommitteeMeetingRepository(session)
    orchestrator = CommitteeMeetingOrchestrator.default(repository, provider)
    orchestrator._test_session = session
    return orchestrator


def test_orchestrator_runs_all_four_agents_in_order(tmp_path: Path) -> None:
    """The fixed meeting flow should call Bull, Bear, Risk, then Chairperson."""
    provider = MockLLMProvider(
        responses=(
            _opinion("Bull Analyst", "Bull Analyst"),
            _opinion("Bear Analyst", "Bear Analyst"),
            _opinion("Risk Manager", "Risk Manager"),
            _chair_result(),
        )
    )
    orchestrator = _orchestrator(tmp_path, provider)

    try:
        result = orchestrator.run("Should we add to NVDA?", "NVDA")
        orchestrator.repository.session.commit()
    finally:
        orchestrator._test_session.close()

    assert result.status is MeetingStatus.COMPLETED
    assert [agent.agent_name for agent in result.agent_results] == [
        "Bull Analyst",
        "Bear Analyst",
        "Risk Manager",
        "Chairperson",
    ]
    assert [request.metadata["agent_name"] for request in provider.requests] == [
        "Bull Analyst",
        "Bear Analyst",
        "Risk Manager",
        "Chairperson",
    ]


def test_orchestrator_persists_messages_and_final_result(tmp_path: Path) -> None:
    """A successful meeting should persist four messages and chairperson JSON."""
    engine = create_sqlite_engine(tmp_path / "persisted.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    provider = MockLLMProvider(
        responses=(
            _opinion("Bull Analyst", "Bull Analyst"),
            _opinion("Bear Analyst", "Bear Analyst"),
            _opinion("Risk Manager", "Risk Manager"),
            _chair_result(),
        )
    )

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        result = CommitteeMeetingOrchestrator.default(repository, provider).run(
            "Should we add to NVDA?",
            "NVDA",
        )
        messages = repository.list_meeting_messages(result.meeting_id)
        meeting = session.get(CommitteeMeeting, result.meeting_id)

    assert result.status is MeetingStatus.COMPLETED
    assert len(messages) == 4
    assert [message.agent_name for message in messages] == [
        "Bull Analyst",
        "Bear Analyst",
        "Risk Manager",
        "Chairperson",
    ]
    assert meeting is not None
    assert meeting.status == MeetingStatus.COMPLETED.value
    assert meeting.result_json == result.result_json
    assert result.result_json == {
        "symbol": "NVDA",
        "action": "watch",
        "confidence": "medium",
        "horizon": "3_months",
        "rationale": "Wait for confirmation.",
        "evidence": [{"summary": "Committee reviewed.", "source": "unit_test"}],
        "risks": ["Valuation risk."],
        "catalysts": ["Earnings update."],
        "data_confidence": "medium",
    }


@dataclass
class FailingAgent:
    """Test double for a committee agent failure."""

    name: str = "Broken Agent"
    role: str = "Broken Role"

    def run(self, context: MeetingContext) -> AgentResult:
        raise RuntimeError("agent failed")


def test_failed_agent_marks_meeting_failed(tmp_path: Path) -> None:
    """The orchestrator should persist FAILED when an agent raises."""
    engine = create_sqlite_engine(tmp_path / "failed.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        orchestrator = CommitteeMeetingOrchestrator(
            repository=repository,
            agents=(FailingAgent(),),
        )
        result = orchestrator.run("Should we add to NVDA?", "NVDA")
        messages = repository.list_meeting_messages(result.meeting_id)
        meeting = session.get(CommitteeMeeting, result.meeting_id)

    assert result.status is MeetingStatus.FAILED
    assert result.error_message == "agent failed"
    assert messages == []
    assert meeting is not None
    assert meeting.status == MeetingStatus.FAILED.value
    assert meeting.error_message == "agent failed"
