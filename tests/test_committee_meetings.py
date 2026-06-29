"""Tests for persistent AI committee meeting domain and DAO support."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from parakeetnest.committee import (
    AgentResult,
    MeetingRequest,
    MeetingResult,
    MeetingStatus,
)
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    run_migrations,
    session_scope,
    table_names,
)


def test_committee_meeting_domain_models_are_typed() -> None:
    """Meeting domain models should capture request, agent, and final result data."""
    request = MeetingRequest(question="Should we add to NVDA?", ticker="NVDA")
    agent_result = AgentResult(
        agent_name="Yoyo",
        role="Chief Risk Officer",
        content="Valuation risk remains elevated.",
    )
    result = MeetingResult(
        meeting_id=1,
        status=MeetingStatus.COMPLETED,
        question=request.question,
        ticker=request.ticker,
        agent_results=(agent_result,),
        result_json={"action": "watch", "confidence": "low"},
    )

    assert request.ticker == "NVDA"
    assert result.status is MeetingStatus.COMPLETED
    assert result.agent_results[0].agent_name == "Yoyo"
    assert result.result_json == {"action": "watch", "confidence": "low"}


def test_initialize_database_creates_committee_meeting_tables(tmp_path: Path) -> None:
    """The lightweight migration path should create committee meeting tables."""
    engine = create_sqlite_engine(tmp_path / "meetings.sqlite3")

    initialize_database(engine)

    inspector = inspect(engine)
    table_set = set(inspector.get_table_names())
    assert "committee_meeting" in table_set
    assert "committee_meeting_message" in table_set
    assert "committee_meeting" in table_names()
    assert "committee_meeting_message" in table_names()


def test_run_migrations_creates_committee_meeting_tables(tmp_path: Path) -> None:
    """The explicit migration runner should create meeting persistence tables."""
    engine = create_sqlite_engine(tmp_path / "meeting_migration.sqlite3")

    run_migrations(engine)

    inspector = inspect(engine)
    table_set = set(inspector.get_table_names())
    assert {"committee_meeting", "committee_meeting_message"}.issubset(table_set)


def test_committee_meeting_repository_lifecycle(tmp_path: Path) -> None:
    """A meeting can be created, messaged, and completed with JSON output."""
    engine = create_sqlite_engine(tmp_path / "meeting_lifecycle.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        meeting = repository.create_meeting(
            question="Should we buy AMD after earnings?",
            ticker="AMD",
        )
        pending_status = meeting.status
        xixi = repository.insert_meeting_message(
            meeting.id,
            agent_name="Xixi",
            role="Chief Fundamental Analyst",
            content="Fundamentals need more validation.",
        )
        yoyo = repository.insert_meeting_message(
            meeting.id,
            agent_name="Yoyo",
            role="Chief Risk Officer",
            content="Downside risk remains the binding constraint.",
        )
        result_json = {
            "action": "watch",
            "confidence": "low",
            "horizon": "3_months",
            "evidence": [{"summary": "Earnings context reviewed.", "source": "test"}],
            "risks": ["Valuation risk."],
            "catalysts": ["Next earnings call."],
        }
        completed = repository.update_meeting_completed(meeting.id, result_json)
        messages = repository.list_meeting_messages(meeting.id)

    assert pending_status == MeetingStatus.PENDING.value
    assert completed.status == MeetingStatus.COMPLETED.value
    assert completed.result_json == result_json
    assert completed.error_message is None
    assert [message.id for message in messages] == [xixi.id, yoyo.id]
    assert [message.agent_name for message in messages] == ["Xixi", "Yoyo"]


def test_committee_meeting_repository_failure_state(tmp_path: Path) -> None:
    """A failed meeting should persist provider-independent error text."""
    engine = create_sqlite_engine(tmp_path / "meeting_failed.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        meeting = repository.create_meeting(
            question="Should we revisit TSLA?",
            ticker="TSLA",
        )
        failed = repository.update_meeting_failed(
            meeting.id,
            error_message="Mock LLM output did not match schema.",
        )

    assert failed.status == MeetingStatus.FAILED.value
    assert failed.error_message == "Mock LLM output did not match schema."
    assert failed.result_json is None
