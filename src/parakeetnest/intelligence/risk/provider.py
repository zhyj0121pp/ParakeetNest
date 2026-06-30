"""Provider abstractions for Risk Layer intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.risk.models import RiskAssessment


class RiskProvider(Protocol):
    """Provider-neutral contract for aggregate risk assessments."""

    def get_risk_assessment(
        self,
        *,
        subject: str | None = None,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        """Return a normalized risk assessment for a generic research subject."""


__all__ = ["RiskProvider"]
