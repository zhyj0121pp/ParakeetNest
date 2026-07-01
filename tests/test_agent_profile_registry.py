"""Tests for committee agent profile registries."""

from __future__ import annotations

import pytest

from parakeetnest.committee.agent_profiles import (
    AgentContextRequirement,
    AgentMemoryPolicy,
    AgentOutputSchema,
    AgentProfile,
    DEFAULT_AGENT_PROFILES,
    DuplicateAgentProfileError,
    InMemoryAgentRegistry,
    UnknownAgentProfileError,
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
        ),
        memory_policy=AgentMemoryPolicy(memory_scopes=("thesis",)),
        output_schema=AgentOutputSchema(
            schema_id="committee_opinion",
            required_fields=("viewpoint", "confidence", "evidence"),
        ),
        capabilities=("fundamental_analysis",),
    )


def test_default_registry_looks_up_profiles_by_agent_id() -> None:
    registry = InMemoryAgentRegistry()

    assert registry.get("xixi") is DEFAULT_AGENT_PROFILES[0]
    assert registry.get(" xixi ") is DEFAULT_AGENT_PROFILES[0]


def test_registry_reports_agent_id_existence() -> None:
    registry = InMemoryAgentRegistry()

    assert registry.exists("dongdong")
    assert registry.exists(" dongdong ")
    assert not registry.exists("unknown_agent")


def test_registry_registers_new_profile() -> None:
    registry = InMemoryAgentRegistry(profiles=())
    profile = _profile()

    registry.register(profile)

    assert registry.get("test_agent") is profile
    assert registry.list() == (profile,)


def test_registry_rejects_duplicate_registration() -> None:
    profile = _profile()
    registry = InMemoryAgentRegistry(profiles=(profile,))

    with pytest.raises(DuplicateAgentProfileError, match="test_agent"):
        registry.register(profile)


def test_registry_raises_clear_exception_for_unknown_agent_id() -> None:
    registry = InMemoryAgentRegistry()

    with pytest.raises(UnknownAgentProfileError, match="Unknown agent profile: nope"):
        registry.get("nope")


def test_registry_lists_profiles_in_registration_order() -> None:
    registry = InMemoryAgentRegistry()

    assert registry.list() == DEFAULT_AGENT_PROFILES
    assert tuple(registry) == DEFAULT_AGENT_PROFILES
    assert [profile.agent_id for profile in registry.list()] == [
        "xixi",
        "dongdong",
        "yoyo",
        "chairman",
    ]
