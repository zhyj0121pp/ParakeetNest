"""Tests for committee agent profile domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from parakeetnest.committee.agent_profiles import (
    CHAIRMAN_PROFILE,
    DEFAULT_AGENT_PROFILES,
    DONGDONG_PROFILE,
    XIXI_PROFILE,
    YOYO_PROFILE,
    AgentContextRequirement,
    AgentMemoryPolicy,
    AgentOutputSchema,
    AgentProfile,
    AgentRole,
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
            required_fields=("viewpoint", "confidence", "evidence"),
        ),
        capabilities=("fundamental_analysis", "valuation_review"),
        research_guardrails=("Research only.",),
    )


def test_agent_profile_creation_normalizes_fields_and_is_immutable() -> None:
    profile = AgentProfile(
        agent_id=" xixi ",
        name=" Xixi ",
        role="fundamental_analyst",
        mandate=" Assess fundamentals. ",
        prompt_source=" committee/prompts/xixi.md ",
        context_requirement=AgentContextRequirement(
            required_sections=(" financials ", "valuation", "financials"),
            optional_sections=(" news ",),
        ),
        memory_policy=AgentMemoryPolicy(memory_scopes=(" thesis ", "thesis")),
        output_schema=AgentOutputSchema(
            schema_id=" committee_opinion ",
            required_fields=(" confidence ", "evidence"),
        ),
        capabilities=(" valuation_review ", "valuation_review"),
        research_guardrails=(" Research only. ",),
    )

    assert profile.agent_id == "xixi"
    assert profile.name == "Xixi"
    assert profile.role is AgentRole.FUNDAMENTAL_ANALYST
    assert profile.mandate == "Assess fundamentals."
    assert profile.context_requirement.required_sections == (
        "financials",
        "valuation",
    )
    assert profile.memory_policy.memory_scopes == ("thesis",)
    assert profile.output_schema.schema_id == "committee_opinion"
    assert profile.capabilities == ("valuation_review",)

    with pytest.raises(FrozenInstanceError):
        profile.name = "Changed"


def test_agent_profile_validation_rejects_invalid_metadata() -> None:
    with pytest.raises(ValueError):
        AgentProfile(
            agent_id="Bad Agent",
            name="Bad",
            role=AgentRole.RISK_OFFICER,
            mandate="Assess risk.",
            prompt_source="committee/prompts/bad.md",
            context_requirement=AgentContextRequirement(),
            memory_policy=AgentMemoryPolicy(),
            output_schema=AgentOutputSchema(
                schema_id="committee_opinion",
                required_fields=("viewpoint",),
            ),
        )

    with pytest.raises(ValueError):
        AgentContextRequirement(
            required_sections=("risk",),
            optional_sections=("risk",),
        )

    with pytest.raises(ValueError):
        AgentMemoryPolicy(max_items=-1)

    with pytest.raises(ValueError):
        AgentOutputSchema(schema_id="", required_fields=("viewpoint",))


def test_agent_profiles_compare_by_value() -> None:
    assert _profile() == _profile()
    assert _profile() != AgentProfile(
        agent_id="other_agent",
        name="Other Agent",
        role=AgentRole.RISK_OFFICER,
        mandate="Assess risk.",
        prompt_source="committee/prompts/other.md",
        context_requirement=AgentContextRequirement(required_sections=("risk",)),
        memory_policy=AgentMemoryPolicy(memory_scopes=("known_risks",)),
        output_schema=AgentOutputSchema(
            schema_id="committee_opinion",
            required_fields=("viewpoint",),
        ),
    )


def test_agent_profile_serialization_round_trips() -> None:
    profile = _profile()

    restored = AgentProfile.from_dict(profile.to_dict())

    assert restored == profile
    assert restored.to_dict()["role"] == "fundamental_analyst"
    assert restored.to_dict()["context_requirement"]["required_sections"] == [
        "financials",
        "valuation",
    ]


def test_initial_default_profiles_describe_only_metadata_and_capabilities() -> None:
    assert DEFAULT_AGENT_PROFILES == (
        XIXI_PROFILE,
        DONGDONG_PROFILE,
        YOYO_PROFILE,
        CHAIRMAN_PROFILE,
    )
    assert [profile.agent_id for profile in DEFAULT_AGENT_PROFILES] == [
        "xixi",
        "dongdong",
        "yoyo",
        "chairman",
    ]
    assert [profile.role for profile in DEFAULT_AGENT_PROFILES] == [
        AgentRole.FUNDAMENTAL_ANALYST,
        AgentRole.OPPORTUNITY_HUNTER,
        AgentRole.RISK_OFFICER,
        AgentRole.CHAIRMAN,
    ]
    assert all(profile.capabilities for profile in DEFAULT_AGENT_PROFILES)
    assert all(
        profile.prompt_source.startswith("committee/prompts/")
        for profile in DEFAULT_AGENT_PROFILES
    )


def test_chairman_profile_requires_complete_recommendation_fields() -> None:
    fields = set(CHAIRMAN_PROFILE.output_schema.required_fields)

    assert {
        "action",
        "confidence",
        "horizon",
        "evidence",
        "risks",
        "catalysts",
    }.issubset(fields)
