"""Fixed committee agent definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBackedCommitteeAgent:
    """Metadata needed by the shared committee agent runtime."""

    name: str
    role: str
    prompt_filename: str


class BullAnalystAgent(PromptBackedCommitteeAgent):
    """Bull-case analyst for the first committee meeting flow."""

    def __init__(self) -> None:
        super().__init__(
            name="Bull Analyst",
            role="Bull Analyst",
            prompt_filename="bull_analyst.md",
        )


class BearAnalystAgent(PromptBackedCommitteeAgent):
    """Bear-case analyst for the first committee meeting flow."""

    def __init__(self) -> None:
        super().__init__(
            name="Bear Analyst",
            role="Bear Analyst",
            prompt_filename="bear_analyst.md",
        )


class RiskManagerAgent(PromptBackedCommitteeAgent):
    """Risk manager for the first committee meeting flow."""

    def __init__(self) -> None:
        super().__init__(
            name="Risk Manager",
            role="Risk Manager",
            prompt_filename="risk_manager.md",
        )


class ChairpersonAgent(PromptBackedCommitteeAgent):
    """Chairperson who produces the final structured result."""

    def __init__(self) -> None:
        super().__init__(
            name="Chairperson",
            role="Chairperson",
            prompt_filename="chairperson.md",
        )
