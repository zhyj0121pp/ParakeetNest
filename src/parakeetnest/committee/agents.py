"""Fixed committee agent definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBackedCommitteeAgent:
    """Metadata needed by the shared committee agent runtime."""

    name: str
    role: str
    prompt_filename: str


class XixiAgent(PromptBackedCommitteeAgent):
    """Xixi, Chief Fundamental Analyst."""

    def __init__(self) -> None:
        super().__init__(
            name="Xixi",
            role="Chief Fundamental Analyst",
            prompt_filename="xixi.md",
        )


class DongdongAgent(PromptBackedCommitteeAgent):
    """Dongdong, Chief Opportunity Hunter."""

    def __init__(self) -> None:
        super().__init__(
            name="Dongdong",
            role="Chief Opportunity Hunter",
            prompt_filename="dongdong.md",
        )


class YoyoAgent(PromptBackedCommitteeAgent):
    """Yoyo, Chief Risk Officer."""

    def __init__(self) -> None:
        super().__init__(
            name="Yoyo",
            role="Chief Risk Officer",
            prompt_filename="yoyo.md",
        )


class ChairmanAgent(PromptBackedCommitteeAgent):
    """Chairman who produces the final structured result."""

    def __init__(self) -> None:
        super().__init__(
            name="Chairman",
            role="Final decision maker",
            prompt_filename="chairman.md",
        )
