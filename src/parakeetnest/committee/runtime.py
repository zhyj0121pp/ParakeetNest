"""Shared prompt rendering and execution runtime for committee agents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from parakeetnest.committee.agent_profiles import (
    AgentProfile,
    AgentRegistry,
    CommitteePromptInput,
    DefaultAgentPromptBuilder,
    create_default_agent_registry,
)
from parakeetnest.committee.base import CommitteeAgent
from parakeetnest.committee.agent_runtime import (
    AgentRequest,
    AgentRuntime as PreparedAgentRuntime,
    DefaultAgentRuntime,
)
from parakeetnest.committee.models import AgentResult, MeetingContext
from parakeetnest.committee.memory import (
    CommitteeMemoryService,
    MemoryImportance,
    MemoryQuery,
    MemorySearchResult,
)
from parakeetnest.context.rendering import MeetingContextPromptRenderer
from parakeetnest.llm import (
    CHAIRMAN_SUMMARY_SCHEMA,
    COMMITTEE_OPINION_SCHEMA,
    LLMProvider,
    OutputParser,
    PORTFOLIO_COMMITTEE_OBSERVATION_SCHEMA,
)
from parakeetnest.llm.models import LLMResponse
from parakeetnest.llm.models import JSONSchema


PROMPT_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class PromptRenderer:
    """Render profile-backed committee prompts for one agent turn."""

    prompt_dir: Path = PROMPT_DIR
    system_filename: str = "system.md"
    context_renderer: MeetingContextPromptRenderer = field(
        default_factory=MeetingContextPromptRenderer
    )
    agent_registry: AgentRegistry = field(default_factory=create_default_agent_registry)
    prompt_builder: DefaultAgentPromptBuilder = field(
        default_factory=DefaultAgentPromptBuilder
    )

    def render(
        self,
        agent: CommitteeAgent,
        context: MeetingContext,
        memory_service: CommitteeMemoryService | None = None,
    ) -> str:
        """Return the final prompt string for one agent turn."""
        profile = self.resolve_profile(agent)
        system_prompt = self._load_markdown(self.system_filename)
        agent_prompt = self._load_agent_prompt(profile)
        rendered_context = self.context_renderer.render(context.research_context)
        rendered_investment_intelligence_context = (
            context.rendered_investment_intelligence_context
            or "- No investment intelligence context available."
        )
        previous_results = self._format_previous_results(context)
        original_request = self._format_original_request(context)
        memory_context = self._render_memory_context(
            memory_service=memory_service,
            context=context,
            agent_id=profile.agent_id,
        )
        return self.prompt_builder.build_committee_prompt(
            CommitteePromptInput(
                profile=profile,
                system_prompt=system_prompt,
                agent_prompt=agent_prompt,
                meeting_id=context.meeting_id,
                ticker=context.ticker,
                question=context.question,
                original_request=original_request,
                meeting_context=rendered_context,
                investment_intelligence_context=(
                    rendered_investment_intelligence_context
                ),
                previous_agent_results=previous_results,
                memory_context=memory_context,
            )
        )

    def resolve_profile(self, agent: CommitteeAgent) -> AgentProfile:
        """Return the registered profile for an agent."""
        return self.agent_registry.get(agent.agent_id)

    def _load_markdown(self, filename: str) -> str:
        return (self.prompt_dir / filename).read_text(encoding="utf-8").strip()

    def _load_agent_prompt(self, profile: AgentProfile) -> str:
        return self._load_markdown(Path(profile.prompt_source).name)

    @staticmethod
    def _format_previous_results(context: MeetingContext) -> str:
        if not context.previous_agent_results:
            return "- None"
        return "\n".join(
            f"- {result.agent_name} ({result.role}): {result.content}"
            for result in context.previous_agent_results
        )

    @staticmethod
    def _format_original_request(context: MeetingContext) -> str:
        request = context.investment_committee_request
        if request is None:
            return context.question

        lines = [
            f"- Ticker: {request.ticker}",
            f"- Topic: {request.topic}",
            f"- Time Horizon: {request.time_horizon.value}",
        ]
        if request.user_question:
            lines.append(f"- User Question: {request.user_question}")
        if request.portfolio_context_notes:
            lines.append(f"- Portfolio Context Notes: {request.portfolio_context_notes}")
        return "\n".join(lines)

    @staticmethod
    def _render_memory_context(
        *,
        memory_service: CommitteeMemoryService | None,
        context: MeetingContext,
        agent_id: str,
    ) -> str | None:
        if memory_service is None:
            return None

        query_kwargs = {
            "meeting_id": str(context.meeting_id) if context.meeting_id else None,
            "ticker": context.ticker or None,
            "importance_at_least": MemoryImportance.MEDIUM,
            "limit": 10,
        }
        general_results = memory_service.search(MemoryQuery(**query_kwargs))
        agent_results = memory_service.search(
            MemoryQuery(agent_id=agent_id, **query_kwargs)
        )
        results = _dedupe_memory_results(general_results + agent_results, limit=10)
        return _format_memory_search_results(results)


@dataclass
class AgentRuntime:
    """Adapt committee agent turns to the provider-neutral agent runtime."""

    llm_provider: LLMProvider
    model: str = "mock-committee"
    temperature: float = 0.0
    prompt_renderer: PromptRenderer = field(default_factory=PromptRenderer)
    parser: OutputParser = field(default_factory=OutputParser)
    execution_runtime: PreparedAgentRuntime | None = None
    memory_service: CommitteeMemoryService | None = None

    def run(self, agent: CommitteeAgent, context: MeetingContext) -> AgentResult:
        """Render, complete, parse, and return a persistable agent result."""
        profile = self.prompt_renderer.resolve_profile(agent)
        response_schema = self._response_schema(profile)
        output_schema_id = profile.output_schema.schema_id
        request = AgentRequest(
            request_id=self._request_id(profile, context),
            agent_id=profile.agent_id,
            prompt=self.prompt_renderer.render(
                agent,
                context,
                memory_service=self.memory_service,
            ),
            output_schema_id=output_schema_id,
            metadata={
                "meeting_id": str(context.meeting_id),
                "agent_name": agent.name,
                "role": agent.role,
            },
        )
        execution_result = self._execution_runtime().execute(request)
        if execution_result.response is None:
            raise RuntimeError(execution_result.error_message)

        response = LLMResponse(
            content=execution_result.response.content,
            model=execution_result.metadata.model,
            provider_name=execution_result.metadata.provider_name,
            finish_reason=execution_result.metadata.finish_reason or "stop",
            retry_count=execution_result.metadata.retry_count,
            latency_ms=execution_result.metadata.latency_ms,
            metadata=dict(execution_result.response.metadata),
        )
        payload = self.parser.parse_json(response, response_schema)
        return AgentResult(
            agent_name=agent.name,
            role=agent.role,
            content=json.dumps(payload, sort_keys=True),
            agent_id=profile.agent_id,
            ticker=context.ticker,
        )

    def _execution_runtime(self) -> PreparedAgentRuntime:
        if self.execution_runtime is not None:
            return self.execution_runtime
        return DefaultAgentRuntime(
            llm_provider=self.llm_provider,
            model=self.model,
            temperature=self.temperature,
            response_schemas={
                "committee_opinion": COMMITTEE_OPINION_SCHEMA,
                "portfolio_committee_observation": (
                    PORTFOLIO_COMMITTEE_OBSERVATION_SCHEMA
                ),
                "chairman_summary": CHAIRMAN_SUMMARY_SCHEMA,
            },
        )

    @staticmethod
    def _response_schema(profile: AgentProfile) -> JSONSchema:
        if profile.output_schema.schema_id == "chairman_summary":
            return CHAIRMAN_SUMMARY_SCHEMA
        if profile.output_schema.schema_id == "portfolio_committee_observation":
            return PORTFOLIO_COMMITTEE_OBSERVATION_SCHEMA
        return COMMITTEE_OPINION_SCHEMA

    @staticmethod
    def _request_id(profile: AgentProfile, context: MeetingContext) -> str:
        return f"meeting_{context.meeting_id}_{profile.agent_id}"


def _format_memory_search_results(
    results: tuple[MemorySearchResult, ...],
) -> str | None:
    if not results:
        return None

    lines = ["Relevant Committee Memories:"]
    for result in results:
        memory = result.memory
        labels = [memory.importance.name, memory.memory_type.name]
        if memory.agent_id is not None:
            labels.append(memory.agent_id)
        label_text = "".join(f"[{label}]" for label in labels)
        lines.append(f"- {label_text} {memory.content}")
    return "\n".join(lines)


def _dedupe_memory_results(
    results: tuple[MemorySearchResult, ...],
    *,
    limit: int,
) -> tuple[MemorySearchResult, ...]:
    unique: list[MemorySearchResult] = []
    seen_memory_ids: set[str] = set()
    for result in results:
        memory_id = result.memory.memory_id
        if memory_id in seen_memory_ids:
            continue
        unique.append(result)
        seen_memory_ids.add(memory_id)
        if len(unique) >= limit:
            break
    return tuple(unique)
