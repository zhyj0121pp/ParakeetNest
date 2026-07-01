"""Tests for permanent investment committee personas."""

from __future__ import annotations

import pytest

from parakeetnest.committee import (
    CommitteeOpinionStyle,
    CommitteePersona,
    CommitteeRole,
    DuplicateCommitteePersonaError,
    PERMANENT_COMMITTEE_PERSONAS,
    PermanentCommitteeService,
)


def test_all_three_permanent_personas_exist() -> None:
    service = PermanentCommitteeService()

    assert [persona.id for persona in service.all()] == [
        "dongdong",
        "xixi",
        "youyou",
    ]
    assert service.get("dongdong").display_name == "Dongdong"
    assert service.get("xixi").display_name == "Xixi"
    assert service.get("youyou").display_name == "Youyou"


def test_daily_committee_order_is_stable() -> None:
    service = PermanentCommitteeService()

    members = service.daily_investment_committee()

    assert [member.id for member in members] == ["dongdong", "xixi", "youyou"]
    assert [member.role_title for member in members] == [
        "Chief Growth Officer",
        "Chief Investment Analyst",
        "Chief Risk Officer",
    ]


def test_persona_ids_are_unique() -> None:
    ids = [persona.id for persona in PERMANENT_COMMITTEE_PERSONAS]

    assert len(ids) == len(set(ids))


def test_personas_include_required_daily_report_metadata() -> None:
    for persona in PERMANENT_COMMITTEE_PERSONAS:
        assert isinstance(persona.role, CommitteeRole)
        assert persona.role_title
        assert persona.responsibility
        assert persona.risk_posture
        assert persona.evidence_requirements
        assert isinstance(persona.writing_style, CommitteeOpinionStyle)


def test_persona_registry_rejects_duplicate_ids() -> None:
    duplicate = CommitteePersona(
        id="dongdong",
        display_name="Duplicate Dongdong",
        role=CommitteeRole.CHIEF_GROWTH_OFFICER,
        role_title="Chief Growth Officer",
        responsibility="Duplicate profile.",
        default_viewpoint="Duplicate profile.",
        risk_posture="Optimistic but evidence-based.",
        evidence_requirements=("Evidence.",),
        writing_style=CommitteeOpinionStyle.OPTIMISTIC_EVIDENCE_BASED,
    )

    with pytest.raises(DuplicateCommitteePersonaError, match="dongdong"):
        PermanentCommitteeService(personas=(PERMANENT_COMMITTEE_PERSONAS[0], duplicate))
