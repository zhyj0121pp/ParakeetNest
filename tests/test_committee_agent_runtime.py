"""Tests for shared committee prompt rendering and agent runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from parakeetnest.committee import (
    AgentResult,
    AgentRuntime,
    ChairmanAgent,
    DongdongAgent,
    MeetingContext,
    PromptRenderer,
    XixiAgent,
    YoyoAgent,
)
from parakeetnest.committee.agent_profiles import XIXI_PROFILE
from parakeetnest.committee.memory import (
    CommitteeMemory,
    CommitteeMemoryService,
    InMemoryCommitteeMemoryRepository,
    MemoryImportance,
    MemoryQuery,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)
from parakeetnest.committee.runtime import PROMPT_DIR
from parakeetnest.context import ContextRequest
from parakeetnest.context import MeetingContext as ResearchMeetingContext
from parakeetnest.context.rendering import MeetingContextPromptRenderer
from parakeetnest.llm import (
    COMMITTEE_OPINION_SCHEMA,
    LLMRequest,
    MockLLMProvider,
    OutputParser,
)


@dataclass(frozen=True)
class RuntimeAgentStub:
    agent_id: str = "xixi"
    name: str = "Test Analyst"
    role: str = "Test Role"
    prompt_filename: str = "xixi.md"


class TrackingAgentRegistry:
    def __init__(self) -> None:
        self.get_calls: list[str] = []

    def exists(self, agent_id: str) -> bool:
        return agent_id == XIXI_PROFILE.agent_id

    def get(self, agent_id: str):
        self.get_calls.append(agent_id)
        return XIXI_PROFILE

    def list(self):
        return (XIXI_PROFILE,)

    def register(self, profile) -> None:
        raise NotImplementedError


class RecordingMemoryService:
    def __init__(self, results: tuple[MemorySearchResult, ...] = ()) -> None:
        self.results = results
        self.queries: list[MemoryQuery] = []

    def search(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        self.queries.append(query)
        return self.results


def _context(*previous_agent_results: AgentResult) -> MeetingContext:
    return MeetingContext(
        meeting_id=1,
        question="Should we add to NVDA?",
        ticker="NVDA",
        research_context=ResearchMeetingContext(
            request=ContextRequest(
                question="Should we add to NVDA?",
                symbols=("NVDA",),
            )
        ),
        previous_agent_results=previous_agent_results,
    )


def _context_with_investment_intelligence() -> MeetingContext:
    return MeetingContext(
        meeting_id=1,
        question="Should we add to NVDA?",
        ticker="NVDA",
        research_context=ResearchMeetingContext(
            request=ContextRequest(
                question="Should we add to NVDA?",
                symbols=("NVDA",),
            )
        ),
        rendered_investment_intelligence_context=(
            "# Investment Intelligence Context\n\n## Risk\n- Overall Level: moderate\n"
        ),
    )


def _opinion() -> str:
    return json.dumps(
        {
            "member_name": "Test Analyst",
            "role": "Test Role",
            "symbol": "NVDA",
            "viewpoint": "Constructive but uncertain.",
            "confidence": "medium",
            "evidence": [{"summary": "Unit test evidence.", "source": "unit_test"}],
            "risks": ["Valuation risk."],
            "catalysts": ["Earnings update."],
        }
    )


def _memory(
    memory_id: str,
    content: str,
    *,
    memory_type: MemoryType = MemoryType.MEETING_SUMMARY,
    importance: MemoryImportance = MemoryImportance.HIGH,
    agent_id: str | None = None,
    ticker: str = "NVDA",
) -> CommitteeMemory:
    return CommitteeMemory(
        memory_id=memory_id,
        scope=MemoryScope.AGENT if agent_id else MemoryScope.COMMITTEE,
        memory_type=memory_type,
        importance=importance,
        content=content,
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        meeting_id="1",
        agent_id=agent_id,
        ticker=ticker,
    )


def _legacy_prompt(agent: RuntimeAgentStub, context: MeetingContext) -> str:
    system_prompt = (PROMPT_DIR / "system.md").read_text(encoding="utf-8").strip()
    agent_prompt = (PROMPT_DIR / agent.prompt_filename).read_text(
        encoding="utf-8"
    ).strip()
    rendered_context = MeetingContextPromptRenderer().render(context.research_context)
    rendered_investment_intelligence_context = (
        context.rendered_investment_intelligence_context
        or "- No investment intelligence context available."
    )
    previous_results = (
        "- None"
        if not context.previous_agent_results
        else "\n".join(
            f"- {result.agent_name} ({result.role}): {result.content}"
            for result in context.previous_agent_results
        )
    )
    return "\n".join(
        (
            "System prompt:",
            system_prompt,
            "",
            "Agent prompt:",
            agent_prompt,
            "",
            f"Meeting ID: {context.meeting_id}",
            f"Ticker: {context.ticker}",
            f"Question: {context.question}",
            "",
            "Original user request:",
            context.question,
            "",
            "Meeting context:",
            rendered_context,
            "",
            "Investment intelligence context:",
            rendered_investment_intelligence_context,
            "",
            "Previous agent results:",
            previous_results,
        )
    )


def test_prompt_renderer_includes_system_prompt() -> None:
    prompt = PromptRenderer().render(RuntimeAgentStub(), _context())

    assert "You are an AI committee member in ParakeetNest." in prompt


def test_prompt_renderer_includes_agent_prompt() -> None:
    prompt = PromptRenderer().render(RuntimeAgentStub(), _context())

    assert "You are Xixi, the Chief Fundamental Analyst." in prompt


def test_prompt_renderer_includes_prior_agent_results() -> None:
    previous = AgentResult(
        agent_name="Dongdong",
        role="Chief Opportunity Hunter",
        content='{"viewpoint": "Margins may compress."}',
    )

    prompt = PromptRenderer().render(RuntimeAgentStub(), _context(previous))

    assert 'Dongdong (Chief Opportunity Hunter): {"viewpoint": "Margins may compress."}' in prompt


def test_prompt_renderer_includes_rendered_meeting_context() -> None:
    prompt = PromptRenderer().render(RuntimeAgentStub(), _context())

    assert "Meeting context:" in prompt
    assert "## Market" in prompt
    assert "## Knowledge Base" in prompt


def test_prompt_renderer_includes_rendered_investment_intelligence_context() -> None:
    prompt = PromptRenderer().render(
        RuntimeAgentStub(),
        _context_with_investment_intelligence(),
    )

    assert "Investment intelligence context:" in prompt
    assert "# Investment Intelligence Context" in prompt
    assert "- Overall Level: moderate" in prompt


def test_prompt_renderer_delegates_profile_lookup_to_agent_registry() -> None:
    registry = TrackingAgentRegistry()

    PromptRenderer(agent_registry=registry).render(XixiAgent(), _context())

    assert registry.get_calls == ["xixi"]


def test_prompt_renderer_preserves_legacy_prompt_text_for_default_agents() -> None:
    context = _context(
        AgentResult(
            agent_name="Dongdong",
            role="Chief Opportunity Hunter",
            content='{"viewpoint": "Margins may compress."}',
        )
    )

    for agent in (XixiAgent(), DongdongAgent(), YoyoAgent(), ChairmanAgent()):
        assert PromptRenderer().render(agent, context) == _legacy_prompt(agent, context)


def test_prompt_renderer_queries_memory_service_with_runtime_filters() -> None:
    memory_service = RecordingMemoryService()

    prompt = PromptRenderer().render(
        RuntimeAgentStub(),
        _context(),
        memory_service=memory_service,
    )

    assert "Relevant Committee Memories:" not in prompt
    assert memory_service.queries == [
        MemoryQuery(
            meeting_id="1",
            ticker="NVDA",
            importance_at_least=MemoryImportance.MEDIUM,
            limit=10,
        ),
        MemoryQuery(
            meeting_id="1",
            agent_id="xixi",
            ticker="NVDA",
            importance_at_least=MemoryImportance.MEDIUM,
            limit=10,
        ),
    ]


def test_prompt_renderer_includes_memory_block_when_relevant_memories_exist() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    memory_service = CommitteeMemoryService(repository)
    repository.save(
        _memory(
            "memory-1",
            "Previous committee preferred HOLD until earnings.",
        )
    )
    repository.save(
        _memory(
            "memory-2",
            "Xixi noted margin resilience.",
            memory_type=MemoryType.AGENT_OBSERVATION,
            importance=MemoryImportance.MEDIUM,
            agent_id="xixi",
        )
    )

    prompt = PromptRenderer().render(
        RuntimeAgentStub(),
        _context(),
        memory_service=memory_service,
    )

    assert "Relevant Committee Memories:" in prompt
    assert (
        "- [HIGH][MEETING_SUMMARY] Previous committee preferred HOLD until earnings."
        in prompt
    )
    assert (
        "- [MEDIUM][AGENT_OBSERVATION][xixi] Xixi noted margin resilience."
        in prompt
    )


def test_prompt_renderer_omits_memory_block_when_no_memories_match() -> None:
    repository = InMemoryCommitteeMemoryRepository()
    memory_service = CommitteeMemoryService(repository)
    repository.save(
        _memory("memory-1", "AAPL memory should not match.", ticker="AAPL")
    )

    prompt = PromptRenderer().render(
        RuntimeAgentStub(),
        _context(),
        memory_service=memory_service,
    )

    assert "Relevant Committee Memories:" not in prompt
    assert "AAPL memory should not match." not in prompt


def test_agent_runtime_calls_llm_provider_once() -> None:
    provider = MockLLMProvider(responses=(_opinion(),))
    runtime = AgentRuntime(llm_provider=provider)

    result = runtime.run(RuntimeAgentStub(), _context())

    assert len(provider.requests) == 1
    assert provider.requests[0].metadata["agent_name"] == "Test Analyst"
    assert result.agent_name == "Test Analyst"
    assert json.loads(result.content)["viewpoint"] == "Constructive but uncertain."


def test_agent_runtime_works_without_memory_service() -> None:
    provider = MockLLMProvider(responses=(_opinion(),))
    runtime = AgentRuntime(llm_provider=provider, memory_service=None)

    runtime.run(RuntimeAgentStub(), _context())

    assert "Relevant Committee Memories:" not in provider.requests[0].prompt


def test_agent_runtime_includes_memory_context_from_memory_service() -> None:
    provider = MockLLMProvider(responses=(_opinion(),))
    memory_service = RecordingMemoryService(
        results=(
            MemorySearchResult(
                memory=_memory(
                    "memory-1",
                    "Runtime should remember prior risk review.",
                    memory_type=MemoryType.RISK_FLAG,
                    importance=MemoryImportance.HIGH,
                ),
                relevance_score=1.0,
            ),
        )
    )
    runtime = AgentRuntime(
        llm_provider=provider,
        memory_service=memory_service,
    )

    runtime.run(RuntimeAgentStub(), _context())

    assert "Relevant Committee Memories:" in provider.requests[0].prompt
    assert "Runtime should remember prior risk review." in provider.requests[0].prompt


def test_agent_runtime_preserves_direct_provider_committee_output() -> None:
    """Migrating the adapter to AgentRuntime should not change committee results."""
    agent = RuntimeAgentStub()
    context = _context()
    migrated_provider = MockLLMProvider(responses=(_opinion(),))
    direct_provider = MockLLMProvider(responses=(_opinion(),))

    migrated_result = AgentRuntime(llm_provider=migrated_provider).run(agent, context)
    direct_response = direct_provider.complete(
        LLMRequest(
            prompt=PromptRenderer().render(agent, context),
            model="mock-committee",
            response_schema=COMMITTEE_OPINION_SCHEMA,
            metadata={
                "meeting_id": str(context.meeting_id),
                "agent_name": agent.name,
                "role": agent.role,
            },
        )
    )
    direct_payload = OutputParser().parse_json(
        direct_response,
        COMMITTEE_OPINION_SCHEMA,
    )
    direct_result = AgentResult(
        agent_name=agent.name,
        role=agent.role,
        content=json.dumps(direct_payload, sort_keys=True),
        agent_id=agent.agent_id,
        ticker=context.ticker,
    )

    assert migrated_result == direct_result
    assert migrated_provider.requests[0].prompt == direct_provider.requests[0].prompt
    assert (
        migrated_provider.requests[0].response_schema
        == direct_provider.requests[0].response_schema
    )
