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

__all__ = [
    "AgentContextRequirement",
    "AgentMemoryPolicy",
    "AgentOutputSchema",
    "AgentProfile",
    "AgentRole",
    "CHAIRMAN_PROFILE",
    "DEFAULT_AGENT_PROFILES",
    "DONGDONG_PROFILE",
    "XIXI_PROFILE",
    "YOYO_PROFILE",
]
