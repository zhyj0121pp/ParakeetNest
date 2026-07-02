"""Tests for portfolio provider abstractions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.portfolio import (
    Holding,
    Portfolio,
    PortfolioAccountNotFoundError,
    PortfolioCashBalance,
    PortfolioDataUnavailableError,
    PortfolioHolding,
    PortfolioProvider,
    PortfolioProviderError,
    PortfolioSnapshot,
)


AS_OF = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)


class InMemoryPortfolioProvider:
    """Minimal provider-neutral portfolio source for contract tests."""

    def __init__(
        self,
        snapshots: dict[str, PortfolioSnapshot],
        unavailable_accounts: set[str] | None = None,
    ) -> None:
        self._snapshots = snapshots
        self._unavailable_accounts = unavailable_accounts or set()

    def list_accounts(self) -> tuple[str, ...]:
        """Return account ids without exposing provider-specific account data."""
        return tuple(self._snapshots)

    def get_portfolio(self, account_id: str) -> Portfolio:
        """Return a minimal provider-neutral portfolio."""
        snapshot = self.get_snapshot(account_id)
        return Portfolio(
            cash_balance=snapshot.total_cash,
            total_market_value=snapshot.total_market_value,
            holdings=tuple(
                Holding(
                    ticker=holding.symbol,
                    quantity=holding.quantity,
                    market_value=holding.market_value,
                    portfolio_weight=holding.weight_in_portfolio(
                        snapshot.total_equity or 0.0
                    ),
                    average_cost=holding.average_cost,
                    unrealized_gain_loss=holding.unrealized_gain_loss,
                )
                for holding in snapshot.holdings
            ),
        )

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        """Return a stored snapshot or raise provider-neutral errors."""
        if account_id in self._unavailable_accounts:
            raise PortfolioDataUnavailableError(
                f"portfolio data unavailable for account: {account_id}"
            )
        try:
            return self._snapshots[account_id]
        except KeyError as exc:
            raise PortfolioAccountNotFoundError(
                f"portfolio account not found: {account_id}"
            ) from exc


def _snapshot(account_id: str) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id=account_id,
        as_of=AS_OF,
        holdings=(
            PortfolioHolding(
                symbol="AAPL",
                name="Apple Inc.",
                quantity=5,
                average_cost=180.0,
                current_price=200.0,
            ),
        ),
        cash_balances=(PortfolioCashBalance(amount=250.0),),
    )


def test_custom_provider_implements_portfolio_provider_protocol() -> None:
    """A custom provider should satisfy the provider-neutral protocol."""
    provider = InMemoryPortfolioProvider({"taxable": _snapshot("taxable")})

    assert isinstance(provider, PortfolioProvider)


def test_list_accounts_returns_account_ids() -> None:
    """Providers should list stable account ids as strings."""
    provider = InMemoryPortfolioProvider(
        {
            "taxable": _snapshot("taxable"),
            "ira": _snapshot("ira"),
        }
    )

    assert provider.list_accounts() == ("taxable", "ira")


def test_get_snapshot_returns_portfolio_snapshot() -> None:
    """Providers should return the shared PortfolioSnapshot domain model."""
    snapshot = _snapshot("taxable")
    provider = InMemoryPortfolioProvider({"taxable": snapshot})

    result = provider.get_snapshot("taxable")

    assert result is snapshot
    assert result.account_id == "taxable"
    assert result.symbols() == ("AAPL",)
    assert result.total_equity == 1250.0


def test_get_portfolio_returns_minimal_portfolio() -> None:
    """Providers should expose the provider-neutral Portfolio architecture."""
    provider = InMemoryPortfolioProvider({"taxable": _snapshot("taxable")})

    portfolio = provider.get_portfolio("taxable")

    assert portfolio.cash_balance == 250.0
    assert portfolio.total_market_value == 1000.0
    assert portfolio.tickers() == ("AAPL",)
    assert portfolio.holdings[0] == Holding(
        ticker="AAPL",
        quantity=5.0,
        market_value=1000.0,
        portfolio_weight=0.8,
        average_cost=180.0,
        unrealized_gain_loss=100.0,
    )


def test_get_snapshot_raises_account_not_found_error() -> None:
    """Missing accounts should use the provider-neutral not-found error."""
    provider = InMemoryPortfolioProvider({"taxable": _snapshot("taxable")})

    with pytest.raises(PortfolioAccountNotFoundError, match="account not found"):
        provider.get_snapshot("missing")


def test_get_snapshot_raises_data_unavailable_error() -> None:
    """Known accounts with unavailable data should use the neutral data error."""
    provider = InMemoryPortfolioProvider(
        {"taxable": _snapshot("taxable")},
        unavailable_accounts={"taxable"},
    )

    with pytest.raises(PortfolioDataUnavailableError, match="data unavailable"):
        provider.get_snapshot("taxable")


def test_portfolio_provider_errors_share_base_type() -> None:
    """Specific portfolio provider errors should be catchable by the base error."""
    assert issubclass(PortfolioAccountNotFoundError, PortfolioProviderError)
    assert issubclass(PortfolioDataUnavailableError, PortfolioProviderError)


def test_provider_neutral_imports_are_available() -> None:
    """The portfolio package should export only provider-neutral abstractions."""
    import parakeetnest.portfolio as portfolio

    assert portfolio.PortfolioProvider is PortfolioProvider
    assert portfolio.Portfolio is Portfolio
    assert portfolio.Holding is Holding
    assert portfolio.PortfolioProviderError is PortfolioProviderError
    assert portfolio.PortfolioAccountNotFoundError is PortfolioAccountNotFoundError
    assert portfolio.PortfolioDataUnavailableError is PortfolioDataUnavailableError
