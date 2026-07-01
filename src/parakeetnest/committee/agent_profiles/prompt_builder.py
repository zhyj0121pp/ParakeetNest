"""Prompt builders for immutable committee agent profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from parakeetnest.committee.agent_profiles.models import AgentProfile


@dataclass(frozen=True)
class CommitteePromptInput:
    """Prompt-ready data for one committee agent turn."""

    profile: AgentProfile
    system_prompt: str
    agent_prompt: str
    meeting_id: int
    ticker: str
    question: str
    original_request: str
    meeting_context: str
    investment_intelligence_context: str
    previous_agent_results: str
    memory_context: str | None = None


class AgentPromptBuilder(Protocol):
    """Build provider-neutral prompts from agent profile metadata."""

    def build(self, profile: AgentProfile) -> str:
        """Return a plain string system prompt for the supplied profile."""

    def build_committee_prompt(self, prompt_input: CommitteePromptInput) -> str:
        """Return a plain string runtime prompt for one committee agent turn."""


class DefaultAgentPromptBuilder:
    """Deterministic prompt builder backed only by AgentProfile metadata."""

    def build(self, profile: AgentProfile) -> str:
        """Return a plain string system prompt for one committee agent."""
        return "\n".join(
            (
                "# Agent System Prompt",
                "",
                "## Identity",
                f"- Name: {profile.name}",
                f"- Agent ID: {profile.agent_id}",
                f"- Profile Version: {profile.version}",
                "",
                "## Role",
                f"- {profile.role.value}",
                "",
                "## Mandate",
                profile.mandate,
                "",
                "## Capabilities",
                *self._format_sequence(profile.capabilities),
                "",
                "## Research Guardrails",
                *self._format_sequence(profile.research_guardrails),
                "",
                "## Output Schema",
                f"- Schema ID: {profile.output_schema.schema_id}",
                f"- Version: {profile.output_schema.version}",
                "- Required Fields:",
                *self._format_sequence(profile.output_schema.required_fields),
            )
        )

    @staticmethod
    def _format_sequence(values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            return ("- None",)
        return tuple(f"- {value}" for value in values)

    def build_committee_prompt(self, prompt_input: CommitteePromptInput) -> str:
        """Return the compatibility committee runtime prompt for one agent turn."""
        sections = [
            "System prompt:",
            prompt_input.system_prompt,
            "",
            "Agent prompt:",
            prompt_input.agent_prompt,
            "",
            f"Meeting ID: {prompt_input.meeting_id}",
            f"Ticker: {prompt_input.ticker}",
            f"Question: {prompt_input.question}",
            "",
            "Original user request:",
            prompt_input.original_request,
            "",
            "Meeting context:",
            prompt_input.meeting_context,
        ]
        if prompt_input.memory_context:
            sections.extend(("", prompt_input.memory_context))
        sections.extend(
            (
                "",
                "Investment intelligence context:",
                prompt_input.investment_intelligence_context,
                "",
                "Previous agent results:",
                prompt_input.previous_agent_results,
            )
        )
        return "\n".join(sections)


__all__ = ["AgentPromptBuilder", "CommitteePromptInput", "DefaultAgentPromptBuilder"]
