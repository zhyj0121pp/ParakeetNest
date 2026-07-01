"""Application-level portfolio intelligence service."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from parakeetnest.portfolio.models import (
    PortfolioAllocation,
    PortfolioHolding,
    PortfolioRiskSummary,
    PortfolioSnapshot,
)
from parakeetnest.portfolio.provider import PortfolioProvider


class PortfolioService:
    """Main provider-backed entry point for portfolio intelligence."""

    def __init__(self, provider: PortfolioProvider) -> None:
        """Initialize the service with one portfolio provider."""
        self._provider = provider

    def list_accounts(self) -> tuple[str, ...]:
        """Return account ids available from the provider."""
        return self._provider.list_accounts()

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        """Return the provider-backed snapshot for an account."""
        return self._provider.get_snapshot(account_id)

    def get_symbols(self, account_id: str) -> tuple[str, ...]:
        """Return holding symbols for an account in snapshot order."""
        return self.get_snapshot(account_id).symbols()

    def get_total_equity(self, account_id: str) -> Decimal:
        """Return total account equity as a Decimal."""
        return _decimal(self.get_snapshot(account_id).total_equity)

    def get_allocation_by_symbol(self, account_id: str) -> tuple[PortfolioAllocation, ...]:
        """Return holding allocations by symbol."""
        snapshot = self.get_snapshot(account_id)
        total_equity = _decimal(snapshot.total_equity)
        if total_equity == 0:
            return ()

        return tuple(
            PortfolioAllocation(
                category=holding.symbol,
                value=_decimal(holding.market_value),
                percent=_weight(holding.market_value, total_equity),
            )
            for holding in snapshot.holdings
        )

    def get_allocation_by_sector(self, account_id: str) -> tuple[PortfolioAllocation, ...]:
        """Return holding allocations grouped by sector."""
        snapshot = self.get_snapshot(account_id)
        total_equity = _decimal(snapshot.total_equity)
        if total_equity == 0:
            return ()

        sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for holding in snapshot.holdings:
            sector = holding.sector or "Unknown"
            sector_values[sector] += _decimal(holding.market_value)

        return tuple(
            PortfolioAllocation(
                category=sector,
                value=value,
                percent=value / total_equity,
            )
            for sector, value in sorted(sector_values.items())
        )

    def get_top_holdings(
        self,
        account_id: str,
        limit: int = 5,
    ) -> tuple[PortfolioHolding, ...]:
        """Return the largest holdings by market value."""
        if limit < 1:
            raise ValueError("top holdings limit must be positive")

        snapshot = self.get_snapshot(account_id)
        return tuple(
            sorted(
                snapshot.holdings,
                key=lambda holding: (-_decimal(holding.market_value), holding.symbol),
            )[:limit]
        )

    def get_risk_summary(self, account_id: str) -> PortfolioRiskSummary:
        """Return a simple deterministic portfolio risk summary."""
        snapshot = self.get_snapshot(account_id)
        if snapshot.is_empty():
            return PortfolioRiskSummary()

        total_equity = _decimal(snapshot.total_equity)
        if total_equity == 0:
            return PortfolioRiskSummary(holding_count=snapshot.holding_count())

        top_holdings = self.get_top_holdings(account_id, limit=5)
        largest_holding = top_holdings[0] if top_holdings else None
        largest_holding_weight = (
            _weight(largest_holding.market_value, total_equity)
            if largest_holding is not None
            else Decimal("0")
        )
        top_5_concentration = sum(
            (_decimal(holding.market_value) for holding in top_holdings),
            Decimal("0"),
        ) / total_equity

        sectors = {holding.sector or "Unknown" for holding in snapshot.holdings}

        return PortfolioRiskSummary(
            concentration_score=float(top_5_concentration),
            largest_position_symbol=largest_holding.symbol if largest_holding else None,
            largest_position_weight=float(largest_holding_weight),
            holding_count=snapshot.holding_count(),
            largest_holding_symbol=largest_holding.symbol if largest_holding else None,
            largest_holding_weight=largest_holding_weight,
            top_5_concentration=top_5_concentration,
            cash_weight=_weight(snapshot.total_cash, total_equity),
            sector_count=len(sectors),
        )


def _decimal(value: Decimal | float | int | str | None) -> Decimal:
    """Return a Decimal using string conversion for provider float values."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _weight(value: Decimal | float | int | str | None, total: Decimal) -> Decimal:
    """Return a stable Decimal fraction for a value over total."""
    if total == 0:
        return Decimal("0")
    return _decimal(value) / total


__all__ = ["PortfolioService"]
