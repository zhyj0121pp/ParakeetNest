"""Tests for shared committee prompt rendering and agent runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass

from parakeetnest.committee import AgentResult, AgentRuntime, MeetingContext, PromptRenderer
from parakeetnest.context import ContextRequest
from parakeetnest.context import MeetingContext as ResearchMeetingContext
from parakeetnest.llm import MockLLMProvider


@dataclass(frozen=True)
class RuntimeAgentStub:
    name: str = "Test Analyst"
    role: str = "Test Role"
    prompt_filename: str = "xixi.md"


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


def test_agent_runtime_calls_llm_provider_once() -> None:
    provider = MockLLMProvider(responses=(_opinion(),))
    runtime = AgentRuntime(llm_provider=provider)

    result = runtime.run(RuntimeAgentStub(), _context())

    assert len(provider.requests) == 1
    assert provider.requests[0].metadata["agent_name"] == "Test Analyst"
    assert result.agent_name == "Test Analyst"
    assert json.loads(result.content)["viewpoint"] == "Constructive but uncertain."
