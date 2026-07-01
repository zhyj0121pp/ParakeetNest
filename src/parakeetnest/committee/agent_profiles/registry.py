"""Provider-neutral registry for committee agent profiles."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from parakeetnest.committee.agent_profiles.defaults import DEFAULT_AGENT_PROFILES
from parakeetnest.committee.agent_profiles.models import AgentProfile


class UnknownAgentProfileError(LookupError):
    """Raised when a requested agent profile is not registered."""


class DuplicateAgentProfileError(ValueError):
    """Raised when registering more than one profile for the same agent ID."""


class AgentRegistry(Protocol):
    """Abstraction for discovering and managing agent profile metadata."""

    def get(self, agent_id: str) -> AgentProfile:
        """Return the profile registered for an agent ID."""

    def list(self) -> tuple[AgentProfile, ...]:
        """Return registered profiles in registration order."""

    def exists(self, agent_id: str) -> bool:
        """Return whether an agent ID has a registered profile."""

    def register(self, profile: AgentProfile) -> None:
        """Register a profile under its stable agent ID."""


class InMemoryAgentRegistry:
    """In-memory registry backed by immutable AgentProfile objects."""

    def __init__(
        self,
        profiles: tuple[AgentProfile, ...] = DEFAULT_AGENT_PROFILES,
    ) -> None:
        self._profiles: dict[str, AgentProfile] = {}
        for profile in profiles:
            self.register(profile)

    def get(self, agent_id: str) -> AgentProfile:
        """Return the profile registered for an agent ID."""
        normalized_agent_id = _normalize_agent_id(agent_id)
        try:
            return self._profiles[normalized_agent_id]
        except KeyError as error:
            available_agent_ids = ", ".join(self._profiles) or "none"
            raise UnknownAgentProfileError(
                "Unknown agent profile: "
                f"{agent_id}. Available agent profiles: {available_agent_ids}"
            ) from error

    def list(self) -> tuple[AgentProfile, ...]:
        """Return registered profiles in registration order."""
        return tuple(self._profiles.values())

    def __iter__(self) -> Iterator[AgentProfile]:
        """Iterate over registered profiles in registration order."""
        return iter(self.list())

    def exists(self, agent_id: str) -> bool:
        """Return whether an agent ID has a registered profile."""
        return _normalize_agent_id(agent_id) in self._profiles

    def register(self, profile: AgentProfile) -> None:
        """Register a profile under its stable agent ID."""
        if profile.agent_id in self._profiles:
            raise DuplicateAgentProfileError(
                f"Agent profile already registered: {profile.agent_id}"
            )

        self._profiles[profile.agent_id] = profile


def create_default_agent_registry() -> AgentRegistry:
    """Create the default registry of committee agent profiles."""
    return InMemoryAgentRegistry()


def _normalize_agent_id(agent_id: str) -> str:
    return str(agent_id).strip()


__all__ = [
    "AgentRegistry",
    "DuplicateAgentProfileError",
    "InMemoryAgentRegistry",
    "UnknownAgentProfileError",
    "create_default_agent_registry",
]
