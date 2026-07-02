"""Tests for the read-only Robinhood portfolio provider adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

import pytest

from parakeetnest.portfolio import (
    PortfolioAccountNotFoundError,
    PortfolioAssetType,
    PortfolioDataUnavailableError,
)
from parakeetnest.portfolio.robinhood import RobinhoodPortfolioProvider


AS_OF = datetime(2026, 7, 2, 13, 30, tzinfo=UTC)


class FakeRobinhoodClient:
    def __init__(
        self,
        *,
        accounts: tuple[str, ...] = ("default",),
        holdings: tuple[Mapping[str, Any], ...] = (),
        cash: Mapping[str, Any] | None = None,
        summary: Mapping[str, Any] | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.accounts = accounts
        self.holdings = holdings
        self.cash = cash or {}
        self.summary = summary or {}
        self.exception = exception
        self.calls: list[tuple[str, str | None]] = []

    def list_accounts(self) -> tuple[str, ...]:
        self.calls.append(("list_accounts", None))
        if self.exception is not None:
            raise self.exception
        return self.accounts

    def get_holdings(self, account_id: str) -> tuple[Mapping[str, Any], ...]:
        self.calls.append(("get_holdings", account_id))
        return self.holdings

    def get_cash(self, account_id: str) -> Mapping[str, Any]:
        self.calls.append(("get_cash", account_id))
        return self.cash

    def get_account_summary(self, account_id: str) -> Mapping[str, Any]:
        self.calls.append(("get_account_summary", account_id))
        return self.summary


def _provider(client: FakeRobinhoodClient) -> RobinhoodPortfolioProvider:
    return RobinhoodPortfolioProvider(client=client, as_of_provider=lambda: AS_OF)


def test_list_accounts_delegates_to_read_only_client() -> None:
    client = FakeRobinhoodClient(accounts=("default", "ira"))
    provider = _provider(client)

    assert provider.list_accounts() == ("default", "ira")
    assert client.calls == [("list_accounts", None)]


def test_get_snapshot_maps_robinhood_holdings_cash_and_summary() -> None:
    client = FakeRobinhoodClient(
        holdings=(
            {
                "symbol": "nvda",
                "name": "NVIDIA Corporation",
                "quantity": "2",
                "average_buy_price": "100.50",
                "price": "150.25",
                "equity": "300.50",
                "sector": "Technology",
                "industry": "Semiconductors",
            },
            {
                "symbol": "spy",
                "name": "SPDR S&P 500 ETF Trust",
                "quantity": "1",
                "average_cost": "450",
                "market_value": "500",
                "asset_type": "etf",
            },
        ),
        cash={"buying_power": "125.75"},
        summary={
            "equity": "926.25",
            "total_unrealized_gain_loss": "149.50",
        },
    )
    provider = _provider(client)

    snapshot = provider.get_snapshot("default")

    assert snapshot.account_id == "default"
    assert snapshot.as_of == AS_OF
    assert snapshot.total_cash == 125.75
    assert snapshot.total_market_value == 926.25
    assert snapshot.total_equity == 926.25
    assert snapshot.total_unrealized_gain_loss == 149.5
    assert snapshot.symbols() == ("NVDA", "SPY")
    assert snapshot.holdings[0].market_value == 300.5
    assert snapshot.holdings[0].current_price == 150.25
    assert snapshot.holdings[0].average_cost == 100.5
    assert snapshot.holdings[0].sector == "Technology"
    assert snapshot.holdings[1].asset_type is PortfolioAssetType.ETF
    assert snapshot.cash_balances[0].amount == 125.75


def test_get_portfolio_maps_minimal_portfolio_model() -> None:
    client = FakeRobinhoodClient(
        holdings=(
            {
                "symbol": "AAPL",
                "quantity": "4",
                "average_buy_price": "175",
                "market_value": "800",
            },
        ),
        cash={"cash": "200"},
    )
    provider = _provider(client)

    portfolio = provider.get_portfolio("default")

    assert portfolio.cash_balance == 200.0
    assert portfolio.total_market_value == 800.0
    assert portfolio.tickers() == ("AAPL",)
    assert portfolio.holdings[0].portfolio_weight == 0.8


def test_empty_portfolio_returns_empty_snapshot() -> None:
    provider = _provider(FakeRobinhoodClient())

    snapshot = provider.get_snapshot("default")

    assert snapshot.is_empty()
    assert snapshot.holdings == ()
    assert snapshot.cash_balances == ()


def test_missing_credentials_fail_gracefully() -> None:
    provider = RobinhoodPortfolioProvider()

    with pytest.raises(PortfolioDataUnavailableError, match="requires credentials"):
        provider.list_accounts()


def test_missing_account_raises_provider_neutral_not_found_error() -> None:
    provider = _provider(FakeRobinhoodClient(accounts=("ira",)))

    with pytest.raises(PortfolioAccountNotFoundError, match="account not found"):
        provider.get_snapshot("default")


def test_expired_session_client_exception_maps_to_data_unavailable() -> None:
    provider = _provider(FakeRobinhoodClient(exception=RuntimeError("session expired")))

    with pytest.raises(PortfolioDataUnavailableError, match="session unavailable"):
        provider.get_snapshot("default")


def test_generic_client_exception_maps_to_data_unavailable() -> None:
    provider = _provider(FakeRobinhoodClient(exception=RuntimeError("provider down")))

    with pytest.raises(PortfolioDataUnavailableError, match="data unavailable"):
        provider.get_snapshot("default")
