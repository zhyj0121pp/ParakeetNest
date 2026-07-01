"""Permanent investment committee persona definitions.

Personas are stable domain identities for daily research reporting. They are
provider-neutral and do not execute agents, call LLMs, fetch data, or trade.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


_PERSONA_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class CommitteeRole(StrEnum):
    """Stable permanent committee role identifiers."""

    CHIEF_GROWTH_OFFICER = "chief_growth_officer"
    CHIEF_INVESTMENT_ANALYST = "chief_investment_analyst"
    CHIEF_RISK_OFFICER = "chief_risk_officer"


class CommitteeOpinionStyle(StrEnum):
    """Stable writing styles used by committee personas."""

    OPTIMISTIC_EVIDENCE_BASED = "optimistic_evidence_based"
    BALANCED_ANALYTICAL = "balanced_analytical"
    CONSERVATIVE_SKEPTICAL = "conservative_skeptical"


@dataclass(frozen=True)
class CommitteePersona:
    """Immutable definition of one permanent investment committee persona."""

    id: str
    display_name: str
    role: CommitteeRole | str
    role_title: str
    responsibility: str
    default_viewpoint: str
    risk_posture: str
    evidence_requirements: tuple[str, ...]
    writing_style: CommitteeOpinionStyle | str
    decision_biases_to_avoid: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        persona_id = str(self.id).strip()
        display_name = _required_text(self.display_name, "display_name")
        role_title = _required_text(self.role_title, "role_title")
        responsibility = _required_text(self.responsibility, "responsibility")
        default_viewpoint = _required_text(
            self.default_viewpoint,
            "default_viewpoint",
        )
        risk_posture = _required_text(self.risk_posture, "risk_posture")

        if not _PERSONA_ID_PATTERN.fullmatch(persona_id):
            raise ValueError("persona id must be lowercase snake_case")
        if isinstance(self.role, str):
            object.__setattr__(self, "role", CommitteeRole(self.role.strip()))
        if isinstance(self.writing_style, str):
            object.__setattr__(
                self,
                "writing_style",
                CommitteeOpinionStyle(self.writing_style.strip()),
            )

        object.__setattr__(self, "id", persona_id)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "role_title", role_title)
        object.__setattr__(self, "responsibility", responsibility)
        object.__setattr__(self, "default_viewpoint", default_viewpoint)
        object.__setattr__(self, "risk_posture", risk_posture)
        object.__setattr__(
            self,
            "evidence_requirements",
            _normalize_unique_strings(
                self.evidence_requirements,
                "evidence_requirements",
            ),
        )
        object.__setattr__(
            self,
            "decision_biases_to_avoid",
            _normalize_unique_strings(
                self.decision_biases_to_avoid,
                "decision_biases_to_avoid",
            ),
        )


@dataclass(frozen=True)
class CommitteeMemberProfile:
    """Daily report profile wrapper for a permanent committee persona."""

    persona: CommitteePersona
    report_section_title: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "report_section_title",
            _required_text(self.report_section_title, "report_section_title"),
        )

    @property
    def id(self) -> str:
        """Return the stable persona ID."""
        return self.persona.id

    @property
    def display_name(self) -> str:
        """Return the committee member display name."""
        return self.persona.display_name

    @property
    def role_title(self) -> str:
        """Return the committee member role title."""
        return self.persona.role_title


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_unique_strings(
    values: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item:
            raise ValueError(f"{field_name} cannot contain blank values")
        if item in seen:
            continue
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


DONGDONG_PERSONA = CommitteePersona(
    id="dongdong",
    display_name="Dongdong",
    role=CommitteeRole.CHIEF_GROWTH_OFFICER,
    role_title="Chief Growth Officer",
    responsibility=(
        "Identify durable growth, AI exposure, innovation curves, catalysts, "
        "and long-term upside."
    ),
    default_viewpoint=(
        "Look first for asymmetric upside, compounding potential, and positive "
        "inflections that are supported by evidence."
    ),
    risk_posture="Optimistic but evidence-based.",
    evidence_requirements=(
        "Growth drivers or product-cycle evidence.",
        "Catalysts that can improve the investment case.",
        "Signals that upside is not purely narrative-driven.",
    ),
    writing_style=CommitteeOpinionStyle.OPTIMISTIC_EVIDENCE_BASED,
    decision_biases_to_avoid=(
        "Story-stock enthusiasm without corroborating evidence.",
        "Ignoring valuation or execution risk when upside is exciting.",
    ),
)

XIXI_PERSONA = CommitteePersona(
    id="xixi",
    display_name="Xixi",
    role=CommitteeRole.CHIEF_INVESTMENT_ANALYST,
    role_title="Chief Investment Analyst",
    responsibility=(
        "Evaluate fundamentals, earnings quality, valuation, competition, "
        "management execution, and thesis durability."
    ),
    default_viewpoint=(
        "Balance upside and downside by weighing business quality, financial "
        "evidence, valuation support, and competitive position."
    ),
    risk_posture="Balanced and analytical.",
    evidence_requirements=(
        "Fundamental evidence from business, financial, or valuation context.",
        "Competitive and execution considerations.",
        "Clear link between evidence and recommendation confidence.",
    ),
    writing_style=CommitteeOpinionStyle.BALANCED_ANALYTICAL,
    decision_biases_to_avoid=(
        "Overweighting recent price action over fundamentals.",
        "Treating cheap valuation as sufficient without business quality.",
    ),
)

YOUYOU_PERSONA = CommitteePersona(
    id="youyou",
    display_name="Youyou",
    role=CommitteeRole.CHIEF_RISK_OFFICER,
    role_title="Chief Risk Officer",
    responsibility=(
        "Protect capital by evaluating downside risk, macro exposure, liquidity, "
        "position sizing, and preservation of optionality."
    ),
    default_viewpoint=(
        "Start with what can go wrong, what evidence is missing, and whether "
        "risk is being adequately compensated."
    ),
    risk_posture="Conservative and skeptical.",
    evidence_requirements=(
        "Downside scenario or risk evidence.",
        "Macro, liquidity, concentration, or data-quality concerns.",
        "Conditions that would invalidate or reduce confidence in the thesis.",
    ),
    writing_style=CommitteeOpinionStyle.CONSERVATIVE_SKEPTICAL,
    decision_biases_to_avoid=(
        "False precision in low-evidence situations.",
        "Underestimating liquidity, macro, or drawdown risk.",
    ),
)


PERMANENT_COMMITTEE_PERSONAS: tuple[CommitteePersona, ...] = (
    DONGDONG_PERSONA,
    XIXI_PERSONA,
    YOUYOU_PERSONA,
)

DAILY_INVESTMENT_COMMITTEE: tuple[CommitteeMemberProfile, ...] = tuple(
    CommitteeMemberProfile(
        persona=persona,
        report_section_title=f"{persona.display_name}'s Opinion",
    )
    for persona in PERMANENT_COMMITTEE_PERSONAS
)


class UnknownCommitteePersonaError(LookupError):
    """Raised when a requested committee persona is not registered."""


class DuplicateCommitteePersonaError(ValueError):
    """Raised when more than one persona has the same stable ID."""


class CommitteePersonaRegistry(Protocol):
    """Provider-neutral registry for permanent committee personas."""

    def all(self) -> tuple[CommitteePersona, ...]:
        """Return all registered personas in stable order."""

    def get(self, persona_id: str) -> CommitteePersona:
        """Return the persona for a stable persona ID."""


class PermanentCommitteeService:
    """In-memory service exposing the stable daily investment committee."""

    def __init__(
        self,
        personas: tuple[CommitteePersona, ...] = PERMANENT_COMMITTEE_PERSONAS,
    ) -> None:
        self._personas: dict[str, CommitteePersona] = {}
        for persona in personas:
            self._register(persona)

    def all(self) -> tuple[CommitteePersona, ...]:
        """Return all permanent personas in stable order."""
        return tuple(self._personas.values())

    def get(self, persona_id: str) -> CommitteePersona:
        """Return one permanent persona by stable ID."""
        normalized_persona_id = str(persona_id).strip()
        try:
            return self._personas[normalized_persona_id]
        except KeyError as error:
            available = ", ".join(self._personas) or "none"
            raise UnknownCommitteePersonaError(
                "Unknown committee persona: "
                f"{persona_id}. Available personas: {available}"
            ) from error

    def daily_investment_committee(self) -> tuple[CommitteeMemberProfile, ...]:
        """Return Dongdong, Xixi, and Youyou in daily report order."""
        return tuple(
            CommitteeMemberProfile(
                persona=persona,
                report_section_title=f"{persona.display_name}'s Opinion",
            )
            for persona in self.all()
        )

    def __iter__(self) -> Iterator[CommitteePersona]:
        """Iterate over permanent personas in stable order."""
        return iter(self.all())

    def _register(self, persona: CommitteePersona) -> None:
        if persona.id in self._personas:
            raise DuplicateCommitteePersonaError(
                f"Committee persona already registered: {persona.id}"
            )
        self._personas[persona.id] = persona


def create_permanent_committee_service() -> PermanentCommitteeService:
    """Create the default permanent committee service."""
    return PermanentCommitteeService()


__all__ = [
    "CommitteeMemberProfile",
    "CommitteeOpinionStyle",
    "CommitteePersona",
    "CommitteePersonaRegistry",
    "CommitteeRole",
    "DAILY_INVESTMENT_COMMITTEE",
    "DONGDONG_PERSONA",
    "DuplicateCommitteePersonaError",
    "PERMANENT_COMMITTEE_PERSONAS",
    "PermanentCommitteeService",
    "UnknownCommitteePersonaError",
    "XIXI_PERSONA",
    "YOUYOU_PERSONA",
    "create_permanent_committee_service",
]
