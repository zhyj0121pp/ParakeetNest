"""Tests for the committee meeting application service."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path

import pytest

from parakeetnest.committee import (
    AgentResult,
    AgentRuntime,
    MeetingResult,
    MeetingStatus,
    PromptRenderer,
)
from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
from parakeetnest.context import ContextRequest
from parakeetnest.context import ContextService
from parakeetnest.context import ContextProviderResult
from parakeetnest.context import ContextMetadata
from parakeetnest.context import MarketDataPoint, MarketSnapshot
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
from parakeetnest.services import MeetingService


@dataclass
class SuccessfulOrchestrator:
    """Test double that records service invocation and returns a final result."""

    calls: list[tuple[int, str, str, ResearchMeetingContext]] = field(default_factory=list)

    def run(
        self,
        meeting_id: int,
        question: str,
        ticker: str,
        research_context: ResearchMeetingContext,
    ) -> MeetingResult:
        self.calls.append((meeting_id, question, ticker, research_context))
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

    calls: list[tuple[int, str, str, ResearchMeetingContext]] = field(default_factory=list)

    def run(
        self,
        meeting_id: int,
        question: str,
        ticker: str,
        research_context: ResearchMeetingContext,
    ) -> MeetingResult:
        self.calls.append((meeting_id, question, ticker, research_context))
        raise RuntimeError("provider unavailable")


@dataclass
class RecordingProvider:
    provider_name: str = "recording_provider"
    requests: list[ContextRequest] = field(default_factory=list)

    def supports(self, request: ContextRequest) -> bool:
        return True

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        self.requests.append(request)
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=ResearchMeetingContext(
                request=request,
                metadata=ContextMetadata(sources=(self.provider_name,)),
                market=MarketSnapshot(
                    source=self.provider_name,
                    points=(
                        MarketDataPoint(
                            symbol=request.symbols[0],
                            source=self.provider_name,
                            price=123.45,
                        ),
                    ),
                ),
            ),
        )


@dataclass(frozen=True)
class ChairmanAgentStub:
    name: str = "Chairman"
    role: str = "Final decision maker"
    prompt_filename: str = "chairman.md"


def _chairman_response() -> str:
    return """
    {
      "symbol": "NVDA",
      "action": "watch",
      "confidence": "medium",
      "horizon": "3_months",
      "rationale": "Wait for confirmation.",
      "evidence": [{"summary": "Committee reviewed.", "source": "unit_test"}],
      "risks": ["Valuation risk."],
      "catalysts": ["Earnings update."],
      "data_confidence": "medium"
    }
    """


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
        service = MeetingService(
            repository=repository,
            orchestrator=orchestrator,
            context_service=ContextService(providers=()),
        )
        with caplog.at_level(logging.INFO, logger="parakeetnest.services.meeting"):
            result = service.run("Should we add to NVDA?", "NVDA")
        meeting = session.get(CommitteeMeeting, result.meeting_id)

    assert result.status is MeetingStatus.COMPLETED
    assert result.result_json is not None
    assert result.result_json["action"] == "watch"
    call = orchestrator.calls[0]
    assert call[:3] == (result.meeting_id, "Should we add to NVDA?", "NVDA")
    assert call[3].request == ContextRequest(
        question="Should we add to NVDA?",
        symbols=("NVDA",),
    )
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
        service = MeetingService(
            repository=repository,
            orchestrator=orchestrator,
            context_service=ContextService(providers=()),
        )
        with caplog.at_level(logging.INFO, logger="parakeetnest.services.meeting"):
            with pytest.raises(RuntimeError, match="provider unavailable"):
                service.run("Should we add to AMD?", "AMD")
        meeting = session.get(CommitteeMeeting, orchestrator.calls[0][0])

    assert meeting is not None
    assert orchestrator.calls[0][:3] == (meeting.id, "Should we add to AMD?", "AMD")
    assert meeting.status == MeetingStatus.FAILED.value
    assert meeting.error_message == "provider unavailable"
    assert meeting.result_json is None
    assert [record.message for record in caplog.records] == [
        "Meeting started",
        "Meeting failed",
    ]


def test_meeting_service_builds_context_before_committee_receives_it(
    tmp_path: Path,
) -> None:
    """The service should invoke providers and pass rendered context to committee flow."""
    engine = create_sqlite_engine(tmp_path / "service_context.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    provider = RecordingProvider()
    llm_provider = MockLLMProvider(responses=(_chairman_response(),))

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        orchestrator = CommitteeMeetingOrchestrator(
            repository=repository,
            agents=(ChairmanAgentStub(),),
            agent_runtime=AgentRuntime(
                llm_provider=llm_provider,
                prompt_renderer=PromptRenderer(),
            ),
        )
        service = MeetingService(
            repository=repository,
            orchestrator=orchestrator,
            context_service=ContextService(providers=(provider,)),
        )
        result = service.run("Should we add to NVDA?", "NVDA")

    assert provider.requests == [
        ContextRequest(question="Should we add to NVDA?", symbols=("NVDA",))
    ]
    prompt = llm_provider.requests[0].prompt
    assert "Meeting context:" in prompt
    assert "## Market" in prompt
    assert "NVDA: price=123.45" in prompt
    assert result.status is MeetingStatus.COMPLETED
