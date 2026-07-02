"""Deterministic in-memory portfolio provider for local development."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping

from parakeetnest.portfolio.exceptions import PortfolioAccountNotFoundError
from parakeetnest.portfolio.models import (
    Holding,
    Portfolio,
    PortfolioAssetType,
    PortfolioCashBalance,
    PortfolioHolding,
    PortfolioPositionType,
    PortfolioSnapshot,
)


class MockPortfolioProvider:
    """Portfolio provider backed by embedded deterministic snapshots."""

    _DEFAULT_AS_OF = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)

    def __init__(
        self,
        snapshots: Mapping[str, PortfolioSnapshot] | None = None,
        portfolios: Mapping[str, Portfolio] | None = None,
    ) -> None:
        self._snapshots = (
            dict(snapshots) if snapshots is not None else _default_snapshots()
        )
        self._portfolios = (
            dict(portfolios)
            if portfolios is not None
            else {
                account_id: _portfolio_from_snapshot(snapshot)
                for account_id, snapshot in self._snapshots.items()
            }
        )

    def list_accounts(self) -> tuple[str, ...]:
        """Return deterministic mock account ids."""
        account_ids = dict.fromkeys((*self._portfolios, *self._snapshots))
        return tuple(account_ids)

    def get_portfolio(self, account_id: str) -> Portfolio:
        """Return a stored minimal portfolio or raise a provider-neutral error."""
        try:
            return self._portfolios[account_id]
        except KeyError as exc:
            raise PortfolioAccountNotFoundError(
                f"portfolio account not found: {account_id}"
            ) from exc

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        """Return a stored snapshot or raise a provider-neutral not-found error."""
        try:
            return self._snapshots[account_id]
        except KeyError as exc:
            raise PortfolioAccountNotFoundError(
                f"portfolio account not found: {account_id}"
            ) from exc


def _default_snapshots() -> dict[str, PortfolioSnapshot]:
    return {
        "mock-main": PortfolioSnapshot(
            account_id="mock-main",
            as_of=MockPortfolioProvider._DEFAULT_AS_OF,
            holdings=(
                PortfolioHolding(
                    symbol="NVDA",
                    name="NVIDIA Corporation",
                    quantity=42,
                    average_cost=118.50,
                    current_price=157.80,
                    sector="Technology",
                    industry="Semiconductors",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
                PortfolioHolding(
                    symbol="MSFT",
                    name="Microsoft Corporation",
                    quantity=16,
                    average_cost=405.25,
                    current_price=493.10,
                    sector="Technology",
                    industry="Software - Infrastructure",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
                PortfolioHolding(
                    symbol="AAPL",
                    name="Apple Inc.",
                    quantity=24,
                    average_cost=182.75,
                    current_price=210.25,
                    sector="Technology",
                    industry="Consumer Electronics",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
                PortfolioHolding(
                    symbol="MU",
                    name="Micron Technology, Inc.",
                    quantity=35,
                    average_cost=92.40,
                    current_price=131.60,
                    sector="Technology",
                    industry="Semiconductors",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
                PortfolioHolding(
                    symbol="CRDO",
                    name="Credo Technology Group Holding Ltd",
                    quantity=80,
                    average_cost=35.10,
                    current_price=68.45,
                    sector="Technology",
                    industry="Communication Equipment",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
                PortfolioHolding(
                    symbol="RKLB",
                    name="Rocket Lab USA, Inc.",
                    quantity=120,
                    average_cost=7.80,
                    current_price=19.35,
                    sector="Industrials",
                    industry="Aerospace & Defense",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
                PortfolioHolding(
                    symbol="OKLO",
                    name="Oklo Inc.",
                    quantity=90,
                    average_cost=10.25,
                    current_price=24.90,
                    sector="Utilities",
                    industry="Utilities - Renewable",
                    asset_type=PortfolioAssetType.EQUITY,
                    position_type=PortfolioPositionType.LONG,
                ),
            ),
            cash_balances=(PortfolioCashBalance(amount=2500.0, currency="USD"),),
        )
    }


def _portfolio_from_snapshot(snapshot: PortfolioSnapshot) -> Portfolio:
    total_equity = snapshot.total_equity or 0.0
    return Portfolio(
        cash_balance=snapshot.total_cash or 0.0,
        total_market_value=snapshot.total_market_value or 0.0,
        holdings=tuple(
            Holding(
                ticker=holding.symbol,
                quantity=holding.quantity,
                market_value=holding.market_value or 0.0,
                portfolio_weight=holding.weight_in_portfolio(total_equity),
                average_cost=holding.average_cost,
                unrealized_gain_loss=holding.unrealized_gain_loss,
            )
            for holding in snapshot.holdings
        ),
    )


__all__ = ["MockPortfolioProvider"]
