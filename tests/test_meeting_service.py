"""Tests for the committee meeting application service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
import logging
from pathlib import Path

import pytest

from parakeetnest.committee import (
    AgentResult,
    AgentRuntime,
    ChairmanAgent,
    DongdongAgent,
    InvestmentCommitteeDecision,
    InvestmentCommitteeRequest,
    MeetingResult,
    MeetingStatus,
    PromptRenderer,
    XixiAgent,
    YoyoAgent,
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

    calls: list[tuple[int, str, str, ResearchMeetingContext, str | None]] = field(
        default_factory=list
    )

    def run(
        self,
        meeting_id: int,
        question: str,
        ticker: str,
        research_context: ResearchMeetingContext,
        rendered_investment_intelligence_context: str | None = None,
        investment_committee_request: InvestmentCommitteeRequest | None = None,
    ) -> MeetingResult:
        self.calls.append(
            (
                meeting_id,
                question,
                ticker,
                research_context,
                rendered_investment_intelligence_context,
            )
        )
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

    calls: list[tuple[int, str, str, ResearchMeetingContext, str | None]] = field(
        default_factory=list
    )

    def run(
        self,
        meeting_id: int,
        question: str,
        ticker: str,
        research_context: ResearchMeetingContext,
        rendered_investment_intelligence_context: str | None = None,
        investment_committee_request: InvestmentCommitteeRequest | None = None,
    ) -> MeetingResult:
        self.calls.append(
            (
                meeting_id,
                question,
                ticker,
                research_context,
                rendered_investment_intelligence_context,
            )
        )
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
    agent_id: str = "chairman"
    name: str = "Chairman"
    role: str = "Final decision maker"
    prompt_filename: str = "chairman.md"


@dataclass
class RecordingInvestmentIntelligenceService:
    rendered_body: str = "# Investment Intelligence Context\n\n## Risk\n- Overall Level: moderate\n"
    calls: list[dict[str, object]] = field(default_factory=list)

    def build_context(
        self,
        *,
        as_of_date: date | None = None,
        universe: str = "US",
        symbol: str = "SPY",
        health_metadata: dict[str, object] | None = None,
    ) -> object:
        self.calls.append(
            {
                "as_of_date": as_of_date,
                "universe": universe,
                "symbol": symbol,
                "health_metadata": health_metadata,
            }
        )
        return object()


@dataclass
class RecordingInvestmentIntelligenceRenderer:
    rendered_body: str = "# Investment Intelligence Context\n\n## Risk\n- Overall Level: moderate\n"
    contexts: list[object] = field(default_factory=list)

    def render(self, context: object) -> str:
        self.contexts.append(context)
        return self.rendered_body


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


def _opinion_response(
    member_name: str,
    role: str,
    viewpoint: str,
    risks: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "member_name": member_name,
            "role": role,
            "symbol": "NVDA",
            "viewpoint": viewpoint,
            "confidence": "medium",
            "evidence": [
                {
                    "summary": f"{member_name} reviewed the request.",
                    "source": "unit_test",
                }
            ],
            "risks": risks or ["Execution risk."],
            "catalysts": ["Earnings update."],
        }
    )


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
    assert call[4] is None
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


def test_meeting_service_builds_investment_intelligence_before_agent_execution(
    tmp_path: Path,
) -> None:
    """The service should render investment intelligence before invoking agents."""
    engine = create_sqlite_engine(tmp_path / "service_investment_intelligence.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    orchestrator = SuccessfulOrchestrator()
    intelligence_service = RecordingInvestmentIntelligenceService()
    intelligence_renderer = RecordingInvestmentIntelligenceRenderer()

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        service = MeetingService(
            repository=repository,
            orchestrator=orchestrator,
            context_service=ContextService(providers=()),
            investment_intelligence_context_service=intelligence_service,
            investment_intelligence_renderer=intelligence_renderer,
        )
        result = service.run("Should we add to NVDA?", "NVDA")

    assert result.status is MeetingStatus.COMPLETED
    assert intelligence_service.calls == [
        {
            "as_of_date": None,
            "universe": "US",
            "symbol": "NVDA",
            "health_metadata": {"meeting_id": str(result.meeting_id)},
        }
    ]
    assert len(intelligence_renderer.contexts) == 1
    assert orchestrator.calls[0][4] == intelligence_renderer.rendered_body


def test_agents_receive_rendered_investment_intelligence_context(
    tmp_path: Path,
) -> None:
    """Rendered investment intelligence should be included in agent prompts."""
    engine = create_sqlite_engine(tmp_path / "service_agent_intelligence.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    llm_provider = MockLLMProvider(responses=(_chairman_response(),))
    intelligence_service = RecordingInvestmentIntelligenceService()
    intelligence_renderer = RecordingInvestmentIntelligenceRenderer(
        rendered_body=(
            "# Investment Intelligence Context\n\n"
            "## Momentum\n"
            "- Symbol: NVDA\n"
            "- Regime: uptrend\n"
        )
    )

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
            context_service=ContextService(providers=()),
            investment_intelligence_context_service=intelligence_service,
            investment_intelligence_renderer=intelligence_renderer,
        )
        result = service.run("Should we add to NVDA?", "NVDA")

    prompt = llm_provider.requests[0].prompt
    assert "Investment intelligence context:" in prompt
    assert "# Investment Intelligence Context" in prompt
    assert "- Symbol: NVDA" in prompt
    assert "- Regime: uptrend" in prompt
    assert result.status is MeetingStatus.COMPLETED


def test_investment_committee_request_executes_through_meeting_service(
    tmp_path: Path,
) -> None:
    """A typed investment committee request should produce a typed report."""
    engine = create_sqlite_engine(tmp_path / "investment_committee.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    llm_provider = MockLLMProvider(
        responses=(
            _opinion_response(
                "Xixi",
                "Chief Fundamental Analyst",
                "Fundamentals remain durable.",
            ),
            _opinion_response(
                "Dongdong",
                "Chief Opportunity Hunter",
                "Bull case depends on AI demand acceleration.",
            ),
            _opinion_response(
                "Yoyo",
                "Chief Risk Officer",
                "Risk is manageable but valuation leaves less margin for error.",
                risks=["Valuation compression.", "Demand normalization."],
            ),
            _chairman_response(),
        )
    )
    intelligence_service = RecordingInvestmentIntelligenceService()
    intelligence_renderer = RecordingInvestmentIntelligenceRenderer(
        rendered_body=(
            "# Investment Intelligence Context\n\n"
            "## Economic Regime\n"
            "- Regime: expansion\n\n"
            "## Sector Rotation\n"
            "- Summary: Technology leads.\n\n"
            "## Risk\n"
            "- Overall Level: moderate\n\n"
            "## Momentum\n"
            "- Symbol: NVDA\n"
            "- Regime: uptrend\n\n"
            "## Market Sentiment\n"
            "- Regime: greed\n"
        )
    )

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        orchestrator = CommitteeMeetingOrchestrator(
            repository=repository,
            agents=(XixiAgent(), DongdongAgent(), YoyoAgent(), ChairmanAgent()),
            agent_runtime=AgentRuntime(
                llm_provider=llm_provider,
                prompt_renderer=PromptRenderer(),
            ),
        )
        service = MeetingService(
            repository=repository,
            orchestrator=orchestrator,
            context_service=ContextService(providers=()),
            investment_intelligence_context_service=intelligence_service,
            investment_intelligence_renderer=intelligence_renderer,
        )
        report = service.execute_investment_committee(
            InvestmentCommitteeRequest(
                ticker="nvda",
                topic="AI infrastructure durability",
                time_horizon="1_year",
                user_question="Should we add after earnings?",
            )
        )
        meeting = session.get(CommitteeMeeting, 1)

    assert report.ticker == "NVDA"
    assert report.topic == "AI infrastructure durability"
    assert report.macro_view == "- Regime: expansion"
    assert report.sector_view == "- Summary: Technology leads."
    assert report.fundamental_view == "Fundamentals remain durable."
    assert report.bull_case == "Bull case depends on AI demand acceleration."
    assert report.risk_view == (
        "Risk is manageable but valuation leaves less margin for error."
    )
    assert "Valuation compression." in report.key_risks
    assert report.decision is InvestmentCommitteeDecision.WATCH
    assert report.confidence == "medium"
    assert report.recommended_action.startswith("watch:")
    assert meeting is not None
    assert meeting.status == MeetingStatus.COMPLETED.value
    assert meeting.result_json["ticker"] == "NVDA"


def test_investment_committee_runtime_receives_original_request(
    tmp_path: Path,
) -> None:
    """The runtime prompt should carry the original request fields."""
    engine = create_sqlite_engine(tmp_path / "investment_committee_prompt.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    llm_provider = MockLLMProvider(responses=(_chairman_response(),))

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        orchestrator = CommitteeMeetingOrchestrator(
            repository=repository,
            agents=(ChairmanAgent(),),
            agent_runtime=AgentRuntime(
                llm_provider=llm_provider,
                prompt_renderer=PromptRenderer(),
            ),
        )
        service = MeetingService(
            repository=repository,
            orchestrator=orchestrator,
            context_service=ContextService(providers=()),
        )
        service.execute_investment_committee(
            InvestmentCommitteeRequest(
                ticker="MSFT",
                topic="Cloud and AI margin durability",
                time_horizon="6_months",
                user_question="Should we hold MSFT?",
                portfolio_context_notes="Already a top-five position.",
            )
        )

    prompt = llm_provider.requests[0].prompt
    assert "Original user request:" in prompt
    assert "- Ticker: MSFT" in prompt
    assert "- Topic: Cloud and AI margin durability" in prompt
    assert "- Time Horizon: 6_months" in prompt
    assert "- User Question: Should we hold MSFT?" in prompt
    assert "- Portfolio Context Notes: Already a top-five position." in prompt
