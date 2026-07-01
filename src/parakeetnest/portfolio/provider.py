"""Provider contract for portfolio data sources."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from parakeetnest.portfolio.models import PortfolioSnapshot


@runtime_checkable
class PortfolioProvider(Protocol):
    """Small contract that all portfolio providers must implement."""

    def list_accounts(self) -> tuple[str, ...]:
        """Return provider-neutral account ids available from this provider."""
        ...

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        """Return a point-in-time provider-neutral snapshot for the account."""
        ...


__all__ = ["PortfolioProvider"]
