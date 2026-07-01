"""Fixed committee agent definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from parakeetnest.committee.agent_profiles import (
    CHAIRMAN_PROFILE,
    DONGDONG_PROFILE,
    XIXI_PROFILE,
    YOYO_PROFILE,
    AgentProfile,
)


@dataclass(frozen=True)
class PromptBackedCommitteeAgent:
    """Profile-backed committee agent handle kept for stable public imports."""

    name: str
    role: str
    prompt_filename: str
    agent_id: str = ""
    profile: AgentProfile | None = None

    def __post_init__(self) -> None:
        if self.agent_id:
            return
        if self.profile is not None:
            object.__setattr__(self, "agent_id", self.profile.agent_id)
            return
        object.__setattr__(self, "agent_id", Path(self.prompt_filename).stem)


def _profile_agent_kwargs(profile: AgentProfile, role: str) -> dict[str, Any]:
    return {
        "name": profile.name,
        "role": role,
        "prompt_filename": Path(profile.prompt_source).name,
        "agent_id": profile.agent_id,
        "profile": profile,
    }


class XixiAgent(PromptBackedCommitteeAgent):
    """Xixi, Chief Fundamental Analyst."""

    def __init__(self) -> None:
        super().__init__(
            **_profile_agent_kwargs(XIXI_PROFILE, "Chief Fundamental Analyst")
        )


class DongdongAgent(PromptBackedCommitteeAgent):
    """Dongdong, Chief Opportunity Hunter."""

    def __init__(self) -> None:
        super().__init__(
            **_profile_agent_kwargs(DONGDONG_PROFILE, "Chief Opportunity Hunter")
        )


class YoyoAgent(PromptBackedCommitteeAgent):
    """Yoyo, Chief Risk Officer."""

    def __init__(self) -> None:
        super().__init__(
            **_profile_agent_kwargs(YOYO_PROFILE, "Chief Risk Officer")
        )


class ChairmanAgent(PromptBackedCommitteeAgent):
    """Chairman who produces the final structured result."""

    def __init__(self) -> None:
        super().__init__(
            **_profile_agent_kwargs(CHAIRMAN_PROFILE, "Final decision maker")
        )
