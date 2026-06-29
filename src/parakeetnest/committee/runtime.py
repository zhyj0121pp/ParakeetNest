"""Shared prompt rendering and execution runtime for committee agents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from parakeetnest.committee.base import CommitteeAgent
from parakeetnest.committee.models import AgentResult, MeetingContext
from parakeetnest.context.rendering import MeetingContextPromptRenderer
from parakeetnest.llm import (
    CHAIRMAN_SUMMARY_SCHEMA,
    COMMITTEE_OPINION_SCHEMA,
    LLMProvider,
    LLMRequest,
    OutputParser,
)
from parakeetnest.llm.models import JSONSchema


PROMPT_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class PromptRenderer:
    """Render prompt markdown and meeting context into one model prompt."""

    prompt_dir: Path = PROMPT_DIR
    system_filename: str = "system.md"
    context_renderer: MeetingContextPromptRenderer = field(
        default_factory=MeetingContextPromptRenderer
    )

    def render(self, agent: CommitteeAgent, context: MeetingContext) -> str:
        """Return the final prompt string for one agent turn."""
        system_prompt = self._load_markdown(self.system_filename)
        agent_prompt = self._load_markdown(agent.prompt_filename)
        rendered_context = self.context_renderer.render(context.research_context)
        previous_results = self._format_previous_results(context)
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
                "Meeting context:",
                rendered_context,
                "",
                "Previous agent results:",
                previous_results,
            )
        )

    def _load_markdown(self, filename: str) -> str:
        return (self.prompt_dir / filename).read_text(encoding="utf-8").strip()

    @staticmethod
    def _format_previous_results(context: MeetingContext) -> str:
        if not context.previous_agent_results:
            return "- None"
        return "\n".join(
            f"- {result.agent_name} ({result.role}): {result.content}"
            for result in context.previous_agent_results
        )


@dataclass
class AgentRuntime:
    """Execute prompt-backed committee agents through the configured LLM provider."""

    llm_provider: LLMProvider
    model: str = "mock-committee"
    prompt_renderer: PromptRenderer = field(default_factory=PromptRenderer)
    parser: OutputParser = field(default_factory=OutputParser)

    def run(self, agent: CommitteeAgent, context: MeetingContext) -> AgentResult:
        """Render, complete, parse, and return a persistable agent result."""
        response_schema = self._response_schema(agent)
        request = LLMRequest(
            prompt=self.prompt_renderer.render(agent, context),
            model=self.model,
            response_schema=response_schema,
            metadata={
                "meeting_id": str(context.meeting_id),
                "agent_name": agent.name,
                "role": agent.role,
            },
        )
        response = self.llm_provider.complete(request)
        payload = self.parser.parse_json(response, response_schema)
        return AgentResult(
            agent_name=agent.name,
            role=agent.role,
            content=json.dumps(payload, sort_keys=True),
        )

    @staticmethod
    def _response_schema(agent: CommitteeAgent) -> JSONSchema:
        if "chair" in agent.name.lower() or "chair" in agent.role.lower():
            return CHAIRMAN_SUMMARY_SCHEMA
        return COMMITTEE_OPINION_SCHEMA
