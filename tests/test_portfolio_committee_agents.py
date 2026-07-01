"""Tests for portfolio committee agent profile definitions."""

from __future__ import annotations

from pathlib import Path

from parakeetnest.committee.agent_profiles import (
    DefaultAgentPromptBuilder,
    InMemoryAgentRegistry,
)
from parakeetnest.portfolio.agents import (
    PORTFOLIO_COMMITTEE_AGENT_PROFILES,
    register_portfolio_committee_agents,
)


EXPECTED_AGENT_IDS = (
    "portfolio_manager",
    "portfolio_risk_manager",
    "sector_analyst",
    "macro_strategist",
)

EXPECTED_AGENT_NAMES = (
    "Portfolio Manager",
    "Risk Manager",
    "Sector Analyst",
    "Macro Strategist",
)


def test_all_portfolio_agents_are_created() -> None:
    assert len(PORTFOLIO_COMMITTEE_AGENT_PROFILES) == 4


def test_all_portfolio_agents_have_stable_ids() -> None:
    assert tuple(
        profile.agent_id for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES
    ) == EXPECTED_AGENT_IDS


def test_all_portfolio_agents_have_clear_names() -> None:
    assert tuple(
        profile.name for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES
    ) == EXPECTED_AGENT_NAMES


def test_all_portfolio_agents_have_portfolio_related_responsibilities() -> None:
    for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES:
        responsibilities = " ".join(
            (
                profile.mandate,
                " ".join(profile.capabilities),
                " ".join(profile.context_requirement.required_sections),
            )
        ).lower()

        assert "portfolio" in responsibilities
        assert profile.context_requirement.required_sections == ("portfolio",)
        assert profile.output_schema.schema_id == "portfolio_committee_observation"


def test_portfolio_agents_can_be_registered_in_existing_registry() -> None:
    registry = InMemoryAgentRegistry(profiles=())

    registered = register_portfolio_committee_agents(registry)

    assert registered == PORTFOLIO_COMMITTEE_AGENT_PROFILES
    assert tuple(profile.agent_id for profile in registry.list()) == EXPECTED_AGENT_IDS
    for agent_id, profile in zip(EXPECTED_AGENT_IDS, registered, strict=True):
        assert registry.get(agent_id) is profile


def test_portfolio_agent_system_prompts_mention_portfolio_context() -> None:
    builder = DefaultAgentPromptBuilder()

    for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES:
        prompt = builder.build(profile).lower()

        assert "portfolio" in prompt
        assert "total equity" in prompt
        assert "top holdings" in prompt
        assert "sector allocation" in prompt
        assert "risk summary" in prompt
        assert "market" in prompt
        assert "macro" in prompt
        assert "investment intelligence" in prompt


def test_portfolio_agent_prompt_sources_mention_portfolio_context() -> None:
    prompt_dir = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "parakeetnest"
        / "committee"
        / "prompts"
    )

    for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES:
        prompt = (prompt_dir / Path(profile.prompt_source).name).read_text(
            encoding="utf-8"
        )
        normalized_prompt = prompt.lower()

        assert "portfolio section" in normalized_prompt
        assert "total equity" in normalized_prompt
        assert "top holdings" in normalized_prompt
        assert "sector allocation" in normalized_prompt
        assert "risk summary" in normalized_prompt


def test_portfolio_agent_prompts_do_not_include_execution_or_brokerage_actions() -> None:
    builder = DefaultAgentPromptBuilder()
    prompt_dir = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "parakeetnest"
        / "committee"
        / "prompts"
    )
    forbidden_phrases = (
        "trade execution",
        "order placement",
        "brokerage",
        "brokerage api",
        "robinhood",
        "automated buy",
        "automated sell",
        "guaranteed returns",
        "guaranteed return",
    )

    for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES:
        system_prompt = builder.build(profile).lower()
        agent_prompt = (prompt_dir / Path(profile.prompt_source).name).read_text(
            encoding="utf-8"
        ).lower()
        combined_prompt = system_prompt + "\n" + agent_prompt

        for forbidden_phrase in forbidden_phrases:
            assert forbidden_phrase not in combined_prompt
