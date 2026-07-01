"""Domain models for committee agent profiles.

Profiles describe committee roles and contracts. They do not execute agents,
render prompts, read memory, call providers, or orchestrate meetings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


_AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class AgentRole(StrEnum):
    """Stable committee role identifiers for profile metadata."""

    FUNDAMENTAL_ANALYST = "fundamental_analyst"
    OPPORTUNITY_HUNTER = "opportunity_hunter"
    RISK_OFFICER = "risk_officer"
    CHAIRMAN = "chairman"
    PORTFOLIO_MANAGER = "portfolio_manager"
    PORTFOLIO_RISK_MANAGER = "portfolio_risk_manager"
    SECTOR_ANALYST = "sector_analyst"
    MACRO_STRATEGIST = "macro_strategist"


@dataclass(frozen=True)
class AgentContextRequirement:
    """Context sections a profile needs or can optionally use."""

    required_sections: tuple[str, ...] = field(default_factory=tuple)
    optional_sections: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        required = _normalize_unique_strings(
            self.required_sections,
            "required_sections",
        )
        optional = _normalize_unique_strings(self.optional_sections, "optional_sections")
        overlap = set(required).intersection(optional)
        if overlap:
            raise ValueError("context sections cannot be both required and optional")

        object.__setattr__(self, "required_sections", required)
        object.__setattr__(self, "optional_sections", optional)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "required_sections": list(self.required_sections),
            "optional_sections": list(self.optional_sections),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentContextRequirement:
        """Build a context requirement from serialized data."""
        return cls(
            required_sections=tuple(payload.get("required_sections", ())),
            optional_sections=tuple(payload.get("optional_sections", ())),
        )


@dataclass(frozen=True)
class AgentMemoryPolicy:
    """Profile-level memory selection policy metadata."""

    memory_scopes: tuple[str, ...] = field(default_factory=tuple)
    max_items: int = 5
    include_unresolved_debates: bool = True

    def __post_init__(self) -> None:
        if self.max_items < 0:
            raise ValueError("max_items must be non-negative")
        object.__setattr__(
            self,
            "memory_scopes",
            _normalize_unique_strings(self.memory_scopes, "memory_scopes"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "memory_scopes": list(self.memory_scopes),
            "max_items": self.max_items,
            "include_unresolved_debates": self.include_unresolved_debates,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentMemoryPolicy:
        """Build a memory policy from serialized data."""
        return cls(
            memory_scopes=tuple(payload.get("memory_scopes", ())),
            max_items=int(payload.get("max_items", 5)),
            include_unresolved_debates=bool(
                payload.get("include_unresolved_debates", True)
            ),
        )


@dataclass(frozen=True)
class AgentOutputSchema:
    """Named output contract metadata for a profile."""

    schema_id: str
    required_fields: tuple[str, ...]
    version: int = 1

    def __post_init__(self) -> None:
        schema_id = self.schema_id.strip()
        if not schema_id:
            raise ValueError("schema_id is required")
        if self.version < 1:
            raise ValueError("version must be positive")

        object.__setattr__(self, "schema_id", schema_id)
        object.__setattr__(
            self,
            "required_fields",
            _normalize_unique_strings(self.required_fields, "required_fields"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "schema_id": self.schema_id,
            "required_fields": list(self.required_fields),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentOutputSchema:
        """Build an output schema reference from serialized data."""
        return cls(
            schema_id=str(payload["schema_id"]),
            required_fields=tuple(payload.get("required_fields", ())),
            version=int(payload.get("version", 1)),
        )


@dataclass(frozen=True)
class AgentProfile:
    """Immutable durable definition of one committee agent."""

    agent_id: str
    name: str
    role: AgentRole | str
    mandate: str
    prompt_source: str
    context_requirement: AgentContextRequirement
    memory_policy: AgentMemoryPolicy
    output_schema: AgentOutputSchema
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    research_guardrails: tuple[str, ...] = field(default_factory=tuple)
    version: int = 1

    def __post_init__(self) -> None:
        agent_id = self.agent_id.strip()
        name = self.name.strip()
        mandate = self.mandate.strip()
        prompt_source = self.prompt_source.strip()

        if not _AGENT_ID_PATTERN.fullmatch(agent_id):
            raise ValueError("agent_id must be lowercase snake_case")
        if not name:
            raise ValueError("name is required")
        if not mandate:
            raise ValueError("mandate is required")
        if not prompt_source:
            raise ValueError("prompt_source is required")
        if self.version < 1:
            raise ValueError("version must be positive")
        if isinstance(self.role, str):
            object.__setattr__(self, "role", AgentRole(self.role.strip()))

        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "mandate", mandate)
        object.__setattr__(self, "prompt_source", prompt_source)
        object.__setattr__(
            self,
            "capabilities",
            _normalize_unique_strings(self.capabilities, "capabilities"),
        )
        object.__setattr__(
            self,
            "research_guardrails",
            _normalize_unique_strings(
                self.research_guardrails,
                "research_guardrails",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "mandate": self.mandate,
            "prompt_source": self.prompt_source,
            "context_requirement": self.context_requirement.to_dict(),
            "memory_policy": self.memory_policy.to_dict(),
            "output_schema": self.output_schema.to_dict(),
            "capabilities": list(self.capabilities),
            "research_guardrails": list(self.research_guardrails),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentProfile:
        """Build an agent profile from serialized data."""
        return cls(
            agent_id=str(payload["agent_id"]),
            name=str(payload["name"]),
            role=str(payload["role"]),
            mandate=str(payload["mandate"]),
            prompt_source=str(payload["prompt_source"]),
            context_requirement=AgentContextRequirement.from_dict(
                payload["context_requirement"]
            ),
            memory_policy=AgentMemoryPolicy.from_dict(payload["memory_policy"]),
            output_schema=AgentOutputSchema.from_dict(payload["output_schema"]),
            capabilities=tuple(payload.get("capabilities", ())),
            research_guardrails=tuple(payload.get("research_guardrails", ())),
            version=int(payload.get("version", 1)),
        )


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
        if item not in seen:
            normalized.append(item)
            seen.add(item)
    return tuple(normalized)
