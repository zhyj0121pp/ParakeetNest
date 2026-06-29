"""Prompt construction interfaces and context builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from parakeetnest.committee.models import CommitteeOpinion, InvestmentContext
from parakeetnest.llm.models import JSONSchema, LLMRequest


@dataclass(frozen=True)
class PromptContext:
    """Memory-first prompt context for committee and report tasks."""

    task: str
    investment_context: InvestmentContext
    opinions: tuple[CommitteeOpinion, ...] = ()
    output_schema: JSONSchema | None = None
    instructions: tuple[str, ...] = field(default_factory=tuple)


class PromptBuilder(Protocol):
    """Build a provider-independent request from prompt context."""

    def build(self, context: PromptContext) -> LLMRequest:
        """Create an LLM request for the supplied context."""


class PromptContextBuilder:
    """Create prompt contexts while preserving remember-before-reason order."""

    def build(
        self,
        task: str,
        investment_context: InvestmentContext,
        *,
        opinions: tuple[CommitteeOpinion, ...] = (),
        output_schema: JSONSchema | None = None,
        instructions: tuple[str, ...] = (),
    ) -> PromptContext:
        """Return structured prompt context for a reasoning task."""
        return PromptContext(
            task=task,
            investment_context=investment_context,
            opinions=opinions,
            output_schema=output_schema,
            instructions=instructions,
        )


class TextPromptBuilder:
    """Default text prompt builder for deterministic tests and future providers."""

    def __init__(self, model: str = "mock-llm") -> None:
        self.model = model

    def build(self, context: PromptContext) -> LLMRequest:
        """Create a plain-text request that leads with memory context."""
        investment_context = context.investment_context
        prompt_parts = [
            f"Task: {context.task}",
            f"Symbol: {investment_context.symbol}",
            "Historical thesis:",
            *self._lines(investment_context.historical_thesis),
            "Historical discussions:",
            *self._lines(investment_context.historical_discussions),
            "Current facts:",
            *self._lines(investment_context.current_facts),
            "Data quality notes:",
            *self._lines(investment_context.data_quality_notes),
        ]
        if context.opinions:
            prompt_parts.append("Committee opinions:")
            prompt_parts.extend(
                f"- {opinion.member_name} ({opinion.role}): {opinion.viewpoint}"
                for opinion in context.opinions
            )
        if context.instructions:
            prompt_parts.append("Instructions:")
            prompt_parts.extend(self._lines(context.instructions))
        return LLMRequest(
            prompt="\n".join(prompt_parts),
            model=self.model,
            system_prompt=(
                "You are part of ParakeetNest. Remember before reasoning. "
                "Return only output that matches the requested JSON schema."
            ),
            response_schema=context.output_schema,
        )

    @staticmethod
    def _lines(items: tuple[str, ...]) -> tuple[str, ...]:
        if not items:
            return ("- None",)
        return tuple(f"- {item}" for item in items)
