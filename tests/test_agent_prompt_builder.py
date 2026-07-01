"""Tests for committee agent prompt builders."""

from __future__ import annotations

from parakeetnest.committee.agent_profiles import (
    DONGDONG_PROFILE,
    XIXI_PROFILE,
    AgentContextRequirement,
    AgentMemoryPolicy,
    AgentOutputSchema,
    AgentProfile,
    DefaultAgentPromptBuilder,
)


def _profile() -> AgentProfile:
    return AgentProfile(
        agent_id="test_agent",
        name="Test Agent",
        role="fundamental_analyst",
        mandate="Evaluate durable business quality.",
        prompt_source="committee/prompts/test.md",
        context_requirement=AgentContextRequirement(
            required_sections=("financials", "valuation"),
            optional_sections=("news",),
        ),
        memory_policy=AgentMemoryPolicy(
            memory_scopes=("thesis", "known_risks"),
            max_items=3,
        ),
        output_schema=AgentOutputSchema(
            schema_id="committee_opinion",
            required_fields=(
                "action",
                "confidence",
                "horizon",
                "evidence",
                "risks",
                "catalysts",
            ),
        ),
        capabilities=("fundamental_analysis", "valuation_review"),
        research_guardrails=("Research only.", "Do not trade."),
    )


def test_default_agent_prompt_builder_generates_prompt_from_profile() -> None:
    prompt = DefaultAgentPromptBuilder().build(_profile())

    assert isinstance(prompt, str)
    assert "# Agent System Prompt" in prompt
    assert "- Name: Test Agent" in prompt
    assert "- Agent ID: test_agent" in prompt
    assert "- fundamental_analyst" in prompt
    assert "Evaluate durable business quality." in prompt
    assert "- fundamental_analysis" in prompt
    assert "- valuation_review" in prompt
    assert "- Research only." in prompt
    assert "- Schema ID: committee_opinion" in prompt
    assert "- action" in prompt
    assert "- catalysts" in prompt


def test_default_agent_prompt_builder_includes_required_sections() -> None:
    prompt = DefaultAgentPromptBuilder().build(_profile())

    for section in (
        "## Identity",
        "## Role",
        "## Mandate",
        "## Capabilities",
        "## Research Guardrails",
        "## Output Schema",
    ):
        assert section in prompt


def test_default_agent_prompt_builder_output_is_deterministic() -> None:
    builder = DefaultAgentPromptBuilder()
    profile = _profile()

    assert builder.build(profile) == builder.build(profile)


def test_default_agent_prompt_builder_varies_by_agent_profile() -> None:
    builder = DefaultAgentPromptBuilder()

    xixi_prompt = builder.build(XIXI_PROFILE)
    dongdong_prompt = builder.build(DONGDONG_PROFILE)

    assert xixi_prompt != dongdong_prompt
    assert "- Name: Xixi" in xixi_prompt
    assert "- Name: Dongdong" in dongdong_prompt
    assert "- fundamental_analyst" in xixi_prompt
    assert "- opportunity_hunter" in dongdong_prompt


def test_default_agent_prompt_builder_does_not_render_runtime_context() -> None:
    prompt = DefaultAgentPromptBuilder().build(_profile())

    assert "committee/prompts/test.md" not in prompt
    prompt_lines = prompt.splitlines()
    assert "- financials" not in prompt_lines
    assert "- valuation" not in prompt_lines
    assert "thesis" not in prompt
    assert "known_risks" not in prompt
    assert "Meeting ID" not in prompt
    assert "Ticker:" not in prompt
