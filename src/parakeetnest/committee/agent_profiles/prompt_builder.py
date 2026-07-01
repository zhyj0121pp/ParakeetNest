"""Prompt builders for immutable committee agent profiles."""

from __future__ import annotations

from typing import Protocol

from parakeetnest.committee.agent_profiles.models import AgentProfile


class AgentPromptBuilder(Protocol):
    """Build a provider-neutral system prompt from agent profile metadata."""

    def build(self, profile: AgentProfile) -> str:
        """Return a plain string system prompt for the supplied profile."""


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


__all__ = ["AgentPromptBuilder", "DefaultAgentPromptBuilder"]
