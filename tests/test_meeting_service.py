"""Tests for the committee meeting application service."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path

import pytest

from parakeetnest.committee import AgentResult, MeetingResult, MeetingStatus
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    session_scope,
)
from parakeetnest.database.models import CommitteeMeeting
from parakeetnest.services import MeetingService


@dataclass
class SuccessfulOrchestrator:
    """Test double that records service invocation and returns a final result."""

    calls: list[tuple[int, str, str]] = field(default_factory=list)

    def run(self, meeting_id: int, question: str, ticker: str) -> MeetingResult:
        self.calls.append((meeting_id, question, ticker))
        return MeetingResult(
            meeting_id=meeting_id,
            status=MeetingStatus.COMPLETED,
            question=question,
            ticker=ticker,
            agent_results=(
                AgentResult(
                    agent_name="Chairman",
                    role="Final decision maker",
                    content='{"action": "watch"}',
                ),
            ),
            result_json={
                "action": "watch",
                "confidence": "medium",
                "horizon": "3_months",
                "evidence": [{"summary": "Committee reviewed.", "source": "test"}],
                "risks": ["Valuation risk."],
                "catalysts": ["Earnings update."],
            },
        )


@dataclass
class FailingOrchestrator:
    """Test double that records service invocation and raises."""

    calls: list[tuple[int, str, str]] = field(default_factory=list)

    def run(self, meeting_id: int, question: str, ticker: str) -> MeetingResult:
        self.calls.append((meeting_id, question, ticker))
        raise RuntimeError("provider unavailable")


def test_meeting_service_runs_successful_meeting_and_persists_completion(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successful service run should create, invoke, complete, and return a result."""
    engine = create_sqlite_engine(tmp_path / "service_success.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    orchestrator = SuccessfulOrchestrator()

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        service = MeetingService(repository=repository, orchestrator=orchestrator)
        with caplog.at_level(logging.INFO, logger="parakeetnest.services.meeting"):
            result = service.run("Should we add to NVDA?", "NVDA")
        meeting = session.get(CommitteeMeeting, result.meeting_id)

    assert result.status is MeetingStatus.COMPLETED
    assert result.result_json is not None
    assert result.result_json["action"] == "watch"
    assert orchestrator.calls == [(result.meeting_id, "Should we add to NVDA?", "NVDA")]
    assert meeting is not None
    assert meeting.status == MeetingStatus.COMPLETED.value
    assert meeting.result_json == result.result_json
    assert meeting.error_message is None
    assert [record.message for record in caplog.records] == [
        "Meeting started",
        "Meeting completed",
    ]


def test_meeting_service_marks_failed_and_rethrows(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failing orchestrator should mark FAILED, save error text, and rethrow."""
    engine = create_sqlite_engine(tmp_path / "service_failed.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    orchestrator = FailingOrchestrator()

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        service = MeetingService(repository=repository, orchestrator=orchestrator)
        with caplog.at_level(logging.INFO, logger="parakeetnest.services.meeting"):
            with pytest.raises(RuntimeError, match="provider unavailable"):
                service.run("Should we add to AMD?", "AMD")
        meeting = session.get(CommitteeMeeting, orchestrator.calls[0][0])

    assert meeting is not None
    assert orchestrator.calls == [(meeting.id, "Should we add to AMD?", "AMD")]
    assert meeting.status == MeetingStatus.FAILED.value
    assert meeting.error_message == "provider unavailable"
    assert meeting.result_json is None
    assert [record.message for record in caplog.records] == [
        "Meeting started",
        "Meeting failed",
    ]
