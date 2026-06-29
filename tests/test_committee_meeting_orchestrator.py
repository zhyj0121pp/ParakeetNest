"""Tests for the first persistent AI committee meeting orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from parakeetnest.app import create_test_app
from parakeetnest.committee import AgentResult, MeetingContext, MeetingStatus
from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
from parakeetnest.context import ContextRequest
from parakeetnest.context import MeetingContext as ResearchMeetingContext
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


def _research_context() -> ResearchMeetingContext:
    return ResearchMeetingContext(
        request=ContextRequest(
            question="Should we add to NVDA?",
            symbols=("NVDA",),
        )
    )


def test_orchestrator_runs_all_four_agents_in_order() -> None:
    """The fixed meeting flow should call Xixi, Dongdong, Yoyo, then Chairman."""
    provider = MockLLMProvider(
        responses=(
            _opinion("Xixi", "Chief Fundamental Analyst"),
            _opinion("Dongdong", "Chief Opportunity Hunter"),
            _opinion("Yoyo", "Chief Risk Officer"),
            _chair_result(),
        )
    )
    app = create_test_app()
    app.agent_runtime.llm_provider = provider

    try:
        meeting = app.meeting_repository.create_meeting("Should we add to NVDA?", "NVDA")
        result = app.committee_orchestrator.run(
            meeting.id,
            "Should we add to NVDA?",
            "NVDA",
            _research_context(),
        )
        app.commit()
    finally:
        app.close()

    assert result.status is MeetingStatus.COMPLETED
    assert [agent.agent_name for agent in result.agent_results] == [
        "Xixi",
        "Dongdong",
        "Yoyo",
        "Chairman",
    ]
    assert [request.metadata["agent_name"] for request in provider.requests] == [
        "Xixi",
        "Dongdong",
        "Yoyo",
        "Chairman",
    ]


def test_orchestrator_persists_messages_and_final_result() -> None:
    """A successful meeting should persist four messages and Chairman JSON."""
    provider = MockLLMProvider(
        responses=(
            _opinion("Xixi", "Chief Fundamental Analyst"),
            _opinion("Dongdong", "Chief Opportunity Hunter"),
            _opinion("Yoyo", "Chief Risk Officer"),
            _chair_result(),
        )
    )
    app = create_test_app()
    app.agent_runtime.llm_provider = provider

    try:
        meeting = app.meeting_repository.create_meeting(
            "Should we add to NVDA?",
            "NVDA",
        )
        result = app.committee_orchestrator.run(
            meeting.id,
            "Should we add to NVDA?",
            "NVDA",
            _research_context(),
        )
        messages = app.meeting_repository.list_meeting_messages(result.meeting_id)
        persisted_meeting = app.session.get(CommitteeMeeting, result.meeting_id)
    finally:
        app.close()

    assert result.status is MeetingStatus.COMPLETED
    assert len(messages) == 4
    assert [message.agent_name for message in messages] == [
        "Xixi",
        "Dongdong",
        "Yoyo",
        "Chairman",
    ]
    assert persisted_meeting is not None
    assert persisted_meeting.status == MeetingStatus.PENDING.value
    assert persisted_meeting.result_json is None
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


def test_failed_agent_error_propagates_without_finalizing_meeting(tmp_path: Path) -> None:
    """The orchestrator should leave lifecycle finalization to MeetingService."""
    engine = create_sqlite_engine(tmp_path / "failed.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        meeting = repository.create_meeting("Should we add to NVDA?", "NVDA")
        orchestrator = CommitteeMeetingOrchestrator(
            repository=repository,
            agents=(FailingAgent(),),
        )
        with pytest.raises(RuntimeError, match="agent failed"):
            orchestrator.run(meeting.id, "Should we add to NVDA?", "NVDA", _research_context())
        messages = repository.list_meeting_messages(meeting.id)
        persisted_meeting = session.get(CommitteeMeeting, meeting.id)

    assert messages == []
    assert persisted_meeting is not None
    assert persisted_meeting.status == MeetingStatus.PENDING.value
    assert persisted_meeting.error_message is None
