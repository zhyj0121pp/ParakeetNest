"""Investment policy skeleton."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InvestmentPolicy:
    """Permanent investment rules used to constrain recommendations."""

    max_position_size: float = 0.20
    max_sector_exposure: float = 0.40
    cash_reserve: float = 0.05
    speculative_allocation_limit: float = 0.10


class PolicyEngine:
    """Evaluate whether candidate recommendations respect policy."""

    def __init__(self, policy: InvestmentPolicy | None = None) -> None:
        """Initialize the policy engine."""
        self.policy = policy or InvestmentPolicy()

    def is_allowed(self, action: str) -> bool:
        """Return whether an action is currently permitted by policy."""
        return action.lower() in {"buy", "hold", "reduce", "watch"}
