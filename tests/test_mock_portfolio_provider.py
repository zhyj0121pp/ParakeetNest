"""Tests for the deterministic mock portfolio provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.portfolio import (
    Holding,
    MockPortfolioProvider,
    Portfolio,
    PortfolioAccountNotFoundError,
    PortfolioCashBalance,
    PortfolioHolding,
    PortfolioProvider,
    PortfolioSnapshot,
)


AS_OF = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
EXPECTED_DEFAULT_SYMBOLS = ("NVDA", "MSFT", "AAPL", "MU", "CRDO", "RKLB", "OKLO")


def _snapshot(account_id: str) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id=account_id,
        as_of=AS_OF,
        holdings=(
            PortfolioHolding(
                symbol="AMD",
                name="Advanced Micro Devices, Inc.",
                quantity=10,
                average_cost=120.0,
                current_price=175.0,
            ),
        ),
        cash_balances=(PortfolioCashBalance(amount=1000.0),),
    )


def test_default_provider_lists_mock_main() -> None:
    """The default provider should expose the embedded mock account."""
    provider = MockPortfolioProvider()

    assert provider.list_accounts() == ("mock-main",)


def test_default_provider_returns_non_empty_portfolio_snapshot() -> None:
    """The default account should return a non-empty PortfolioSnapshot."""
    provider = MockPortfolioProvider()

    snapshot = provider.get_snapshot("mock-main")

    assert isinstance(snapshot, PortfolioSnapshot)
    assert snapshot.account_id == "mock-main"
    assert snapshot.holding_count() > 0
    assert snapshot.cash_balances == (PortfolioCashBalance(amount=2500.0),)
    assert snapshot.total_equity > 0
    assert snapshot.is_empty() is False


def test_default_provider_returns_minimal_portfolio() -> None:
    """The mock provider should expose Story 39.1 portfolio models."""
    provider = MockPortfolioProvider()

    portfolio = provider.get_portfolio("mock-main")

    assert isinstance(portfolio, Portfolio)
    assert portfolio.cash_balance == 2500.0
    assert portfolio.total_market_value > 0
    assert portfolio.tickers() == EXPECTED_DEFAULT_SYMBOLS
    assert portfolio.holdings[0].ticker == "NVDA"
    assert portfolio.holdings[0].average_cost == 118.5
    assert portfolio.holdings[0].unrealized_gain_loss is not None


def test_default_holdings_include_expected_symbols() -> None:
    """Default holdings should cover the expected local-development symbols."""
    provider = MockPortfolioProvider()

    assert provider.get_snapshot("mock-main").symbols() == EXPECTED_DEFAULT_SYMBOLS


def test_custom_snapshots_override_defaults() -> None:
    """Passing snapshots should use only those snapshots instead of defaults."""
    snapshot = _snapshot("custom")
    provider = MockPortfolioProvider({"custom": snapshot})

    assert provider.list_accounts() == ("custom",)
    assert provider.get_snapshot("custom") is snapshot
    with pytest.raises(PortfolioAccountNotFoundError):
        provider.get_snapshot("mock-main")


def test_custom_portfolios_can_be_provided_directly() -> None:
    """Tests can inject minimal portfolios without brokerage integration."""
    portfolio = Portfolio(
        cash_balance=100.0,
        total_market_value=500.0,
        holdings=(
            Holding(
                ticker=" amd ",
                quantity=4,
                market_value=500,
                portfolio_weight=0.8333333333,
            ),
        ),
    )
    provider = MockPortfolioProvider(snapshots={}, portfolios={"paper": portfolio})

    assert provider.list_accounts() == ("paper",)
    assert provider.get_portfolio("paper") is portfolio
    with pytest.raises(PortfolioAccountNotFoundError):
        provider.get_snapshot("paper")


def test_empty_snapshots_are_supported() -> None:
    """An explicitly empty snapshot mapping should produce an empty provider."""
    provider = MockPortfolioProvider({})

    assert provider.list_accounts() == ()
    with pytest.raises(PortfolioAccountNotFoundError, match="account not found"):
        provider.get_snapshot("mock-main")


def test_unknown_account_raises_account_not_found_error() -> None:
    """Missing accounts should use the provider-neutral not-found error."""
    provider = MockPortfolioProvider()

    with pytest.raises(PortfolioAccountNotFoundError, match="account not found"):
        provider.get_snapshot("missing")

    with pytest.raises(PortfolioAccountNotFoundError, match="account not found"):
        provider.get_portfolio("missing")


def test_mock_provider_implements_portfolio_provider_contract() -> None:
    """The mock provider should be usable through the provider protocol."""
    provider: PortfolioProvider = MockPortfolioProvider()

    assert isinstance(provider, PortfolioProvider)
    assert provider.get_snapshot("mock-main").symbols() == EXPECTED_DEFAULT_SYMBOLS
