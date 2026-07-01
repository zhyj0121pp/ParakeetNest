"""Committee agent profile domain package."""

from parakeetnest.committee.agent_profiles.defaults import (
    CHAIRMAN_PROFILE,
    DEFAULT_AGENT_PROFILES,
    DONGDONG_PROFILE,
    XIXI_PROFILE,
    YOYO_PROFILE,
)
from parakeetnest.committee.agent_profiles.models import (
    AgentContextRequirement,
    AgentMemoryPolicy,
    AgentOutputSchema,
    AgentProfile,
    AgentRole,
)
from parakeetnest.committee.agent_profiles.registry import (
    AgentRegistry,
    DuplicateAgentProfileError,
    InMemoryAgentRegistry,
    UnknownAgentProfileError,
    create_default_agent_registry,
)

__all__ = [
    "AgentContextRequirement",
    "AgentMemoryPolicy",
    "AgentOutputSchema",
    "AgentProfile",
    "AgentRegistry",
    "AgentRole",
    "CHAIRMAN_PROFILE",
    "DEFAULT_AGENT_PROFILES",
    "DONGDONG_PROFILE",
    "DuplicateAgentProfileError",
    "InMemoryAgentRegistry",
    "UnknownAgentProfileError",
    "XIXI_PROFILE",
    "YOYO_PROFILE",
    "create_default_agent_registry",
]
