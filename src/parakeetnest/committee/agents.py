"""Fixed LLM-backed committee agents for persistent meetings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from parakeetnest.committee.models import AgentResult, MeetingContext
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
class FixedCommitteeAgent:
    """Base implementation for a fixed committee agent."""

    name: str
    role: str
    prompt_file: str
    llm_provider: LLMProvider
    model: str = "mock-committee"
    response_schema: JSONSchema = field(default_factory=lambda: COMMITTEE_OPINION_SCHEMA)
    parser: OutputParser = field(default_factory=OutputParser)

    def run(self, context: MeetingContext) -> AgentResult:
        """Call the configured LLM provider and return a persistable result."""
        request = LLMRequest(
            prompt=self._build_prompt(context),
            model=self.model,
            system_prompt=self._load_system_prompt(),
            response_schema=self.response_schema,
            metadata={
                "meeting_id": str(context.meeting_id),
                "agent_name": self.name,
                "role": self.role,
            },
        )
        response = self.llm_provider.complete(request)
        payload = self.parser.parse_json(response, self.response_schema)
        return AgentResult(
            agent_name=self.name,
            role=self.role,
            content=json.dumps(payload, sort_keys=True),
        )

    def _build_prompt(self, context: MeetingContext) -> str:
        role_prompt = (PROMPT_DIR / self.prompt_file).read_text(encoding="utf-8")
        previous_results = "\n".join(
            f"- {result.agent_name} ({result.role}): {result.content}"
            for result in context.previous_agent_results
        )
        if not previous_results:
            previous_results = "- None"
        return "\n".join(
            (
                role_prompt,
                "",
                f"Meeting ID: {context.meeting_id}",
                f"Ticker: {context.ticker}",
                f"Question: {context.question}",
                "",
                "Previous agent results:",
                previous_results,
            )
        )

    @staticmethod
    def _load_system_prompt() -> str:
        return (PROMPT_DIR / "system.md").read_text(encoding="utf-8")


class BullAnalystAgent(FixedCommitteeAgent):
    """Bull-case analyst for the first committee meeting flow."""

    def __init__(self, llm_provider: LLMProvider, model: str = "mock-committee") -> None:
        super().__init__(
            name="Bull Analyst",
            role="Bull Analyst",
            prompt_file="bull_analyst.md",
            llm_provider=llm_provider,
            model=model,
            response_schema=COMMITTEE_OPINION_SCHEMA,
        )


class BearAnalystAgent(FixedCommitteeAgent):
    """Bear-case analyst for the first committee meeting flow."""

    def __init__(self, llm_provider: LLMProvider, model: str = "mock-committee") -> None:
        super().__init__(
            name="Bear Analyst",
            role="Bear Analyst",
            prompt_file="bear_analyst.md",
            llm_provider=llm_provider,
            model=model,
            response_schema=COMMITTEE_OPINION_SCHEMA,
        )


class RiskManagerAgent(FixedCommitteeAgent):
    """Risk manager for the first committee meeting flow."""

    def __init__(self, llm_provider: LLMProvider, model: str = "mock-committee") -> None:
        super().__init__(
            name="Risk Manager",
            role="Risk Manager",
            prompt_file="risk_manager.md",
            llm_provider=llm_provider,
            model=model,
            response_schema=COMMITTEE_OPINION_SCHEMA,
        )


class ChairpersonAgent(FixedCommitteeAgent):
    """Chairperson who produces the final structured result."""

    def __init__(self, llm_provider: LLMProvider, model: str = "mock-committee") -> None:
        super().__init__(
            name="Chairperson",
            role="Chairperson",
            prompt_file="chairperson.md",
            llm_provider=llm_provider,
            model=model,
            response_schema=CHAIRMAN_SUMMARY_SCHEMA,
        )
