"""Provider abstractions for Risk Layer intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.risk.models import RiskSignal


class RiskProvider(Protocol):
    """Provider-neutral contract for normalized risk signals."""

    def get_risk_signals(
        self,
        *,
        subject: str | None = None,
        as_of_date: date | None = None,
    ) -> list[RiskSignal]:
        """Return normalized risk signals for a generic research subject."""


__all__ = ["RiskProvider"]
