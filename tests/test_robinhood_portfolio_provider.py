"""Tests for the read-only Robinhood portfolio provider adapter."""

from __future__ import annotations

from datetime import UTC, datetime
import pickle
from pathlib import Path
from typing import Any, Mapping

import pytest

from parakeetnest.portfolio import (
    PortfolioAccountNotFoundError,
    PortfolioAssetType,
    PortfolioDataUnavailableError,
)
from parakeetnest.portfolio.robinhood import (
    RobinhoodPortfolioProvider,
    _RobinStocksReadOnlyClient,
)


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


class FakeRobinStocksResponse:
    def __init__(self, exception: Exception | None = None) -> None:
        self.exception = exception

    def raise_for_status(self) -> None:
        if self.exception is not None:
            raise self.exception


class FakeRobinStocksModule:
    def __init__(self, *, cache_exception: Exception | None = None) -> None:
        self.login_calls: list[dict[str, Any]] = []
        self.session_updates: list[tuple[str, str | None]] = []
        self.login_states: list[bool] = []
        self.cache_exception = cache_exception
        self.profiles = self
        self.account = self

    def login(self, **kwargs: Any) -> Mapping[str, str]:
        self.login_calls.append(kwargs)
        if kwargs.get("store_session"):
            cache_path = Path(kwargs["pickle_path"]) / (
                f"robinhood{kwargs.get('pickle_name', '')}.pickle"
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("wb") as session_file:
                pickle.dump(
                    {
                        "token_type": "Bearer",
                        "access_token": "cached-token",
                        "refresh_token": "refresh-token",
                        "device_token": "device-token",
                    },
                    session_file,
                )
        return {
            "token_type": "Bearer",
            "access_token": "cached-token",
            "refresh_token": "refresh-token",
        }

    def update_session(self, key: str, value: str | None) -> None:
        self.session_updates.append((key, value))

    def set_login_state(self, value: bool) -> None:
        self.login_states.append(value)

    def positions_url(self) -> str:
        return "https://example.invalid/positions/"

    def request_get(self, *args: Any, **kwargs: Any) -> FakeRobinStocksResponse:
        return FakeRobinStocksResponse(self.cache_exception)

    def load_account_profile(self, info: Any = None) -> Mapping[str, str]:
        return {"account_number": "RH1234"}

    def load_portfolio_profile(self, info: Any = None) -> Mapping[str, str]:
        return {"equity": "1000"}

    def build_holdings(self) -> Mapping[str, Mapping[str, str]]:
        return {}


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


def test_default_account_alias_uses_first_available_robinhood_account() -> None:
    client = FakeRobinhoodClient(accounts=("RH123",))
    provider = _provider(client)

    snapshot = provider.get_snapshot("default")

    assert snapshot.account_id == "RH123"
    assert client.calls == [
        ("list_accounts", None),
        ("get_holdings", "RH123"),
        ("get_cash", "RH123"),
        ("get_account_summary", "RH123"),
    ]


def test_missing_credentials_fail_gracefully() -> None:
    provider = RobinhoodPortfolioProvider()

    with pytest.raises(PortfolioDataUnavailableError, match="requires credentials"):
        provider.list_accounts()


def test_robin_stocks_client_uses_cached_session_when_available(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "robinhood.pickle"
    with cache_path.open("wb") as session_file:
        pickle.dump(
            {
                "token_type": "Bearer",
                "access_token": "cached-token",
                "refresh_token": "refresh-token",
            },
            session_file,
        )
    module = FakeRobinStocksModule()
    client = _RobinStocksReadOnlyClient(
        username=None,
        password=None,
        session_token=None,
        session_cache_path=cache_path,
        module=module,
    )

    assert client.list_accounts() == ("RH1234",)
    assert module.login_calls == []
    assert module.session_updates == [("Authorization", "Bearer cached-token")]
    assert module.login_states == [True]


def test_robin_stocks_client_falls_back_to_username_password_when_cache_missing(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "robinhood.pickle"
    module = FakeRobinStocksModule()
    client = _RobinStocksReadOnlyClient(
        username="xixi",
        password="secret",
        session_token=None,
        session_cache_path=cache_path,
        module=module,
    )

    assert client.list_accounts() == ("RH1234",)
    assert len(module.login_calls) == 1
    assert module.login_calls[0]["username"] == "xixi"
    assert module.login_calls[0]["password"] == "secret"
    assert module.login_calls[0]["store_session"] is True
    assert cache_path.exists()


def test_robin_stocks_client_invalid_cache_triggers_relogin(tmp_path: Path) -> None:
    cache_path = tmp_path / "robinhood.pickle"
    with cache_path.open("wb") as session_file:
        pickle.dump(
            {
                "token_type": "Bearer",
                "access_token": "expired-token",
                "refresh_token": "refresh-token",
            },
            session_file,
        )
    module = FakeRobinStocksModule(cache_exception=RuntimeError("expired"))
    client = _RobinStocksReadOnlyClient(
        username="xixi",
        password="secret",
        session_token=None,
        session_cache_path=cache_path,
        module=module,
    )

    assert client.list_accounts() == ("RH1234",)
    assert len(module.login_calls) == 1
    assert module.login_calls[0]["username"] == "xixi"
    assert module.login_calls[0]["password"] == "secret"
    assert module.login_calls[0]["store_session"] is True


def test_robin_stocks_client_does_not_print_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cache_path = tmp_path / "robinhood.pickle"
    module = FakeRobinStocksModule()
    client = _RobinStocksReadOnlyClient(
        username="xixi",
        password="secret",
        session_token=None,
        session_cache_path=cache_path,
        module=module,
    )

    client.list_accounts()

    captured = capsys.readouterr()
    assert "xixi" not in captured.out
    assert "secret" not in captured.out
    assert "cached-token" not in captured.out
    assert "xixi" not in captured.err
    assert "secret" not in captured.err
    assert "cached-token" not in captured.err


def test_missing_explicit_account_raises_provider_neutral_not_found_error() -> None:
    provider = _provider(FakeRobinhoodClient(accounts=("ira",)))

    with pytest.raises(PortfolioAccountNotFoundError, match="account not found"):
        provider.get_snapshot("missing")


def test_expired_session_client_exception_maps_to_data_unavailable() -> None:
    provider = _provider(FakeRobinhoodClient(exception=RuntimeError("session expired")))

    with pytest.raises(PortfolioDataUnavailableError, match="session unavailable"):
        provider.get_snapshot("default")


def test_generic_client_exception_maps_to_data_unavailable() -> None:
    provider = _provider(FakeRobinhoodClient(exception=RuntimeError("provider down")))

    with pytest.raises(PortfolioDataUnavailableError, match="data unavailable"):
        provider.get_snapshot("default")
