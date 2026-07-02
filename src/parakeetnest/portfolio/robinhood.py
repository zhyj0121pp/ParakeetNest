"""Read-only Robinhood portfolio provider adapter."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from importlib import import_module
from math import isfinite
from pathlib import Path
import pickle
from types import ModuleType
from typing import Any, Protocol

from parakeetnest.portfolio.exceptions import (
    PortfolioAccountNotFoundError,
    PortfolioDataUnavailableError,
    PortfolioProviderError,
)
from parakeetnest.portfolio.models import (
    Holding,
    Portfolio,
    PortfolioAssetType,
    PortfolioCashBalance,
    PortfolioHolding,
    PortfolioSnapshot,
)


class RobinhoodClient(Protocol):
    """Read-only client contract consumed by the Robinhood provider."""

    def list_accounts(self) -> tuple[str, ...]:
        """Return available account ids."""
        ...

    def get_holdings(self, account_id: str) -> tuple[Mapping[str, Any], ...]:
        """Return raw read-only holding payloads for an account."""
        ...

    def get_cash(self, account_id: str) -> Mapping[str, Any]:
        """Return raw cash or buying-power payload for an account."""
        ...

    def get_account_summary(self, account_id: str) -> Mapping[str, Any]:
        """Return raw read-only account summary payload for an account."""
        ...


class RobinhoodPortfolioProvider:
    """Portfolio provider backed by read-only Robinhood account data."""

    provider_name = "robinhood"

    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        session_token: str | None = None,
        session_cache_path: str | Path | None = None,
        client: RobinhoodClient | None = None,
        as_of_provider: Any | None = None,
    ) -> None:
        self._username = _normalize_secret(username)
        self._password = _normalize_secret(password)
        self._session_token = _normalize_secret(session_token)
        self._session_cache_path = _normalize_cache_path(session_cache_path)
        self._client = client
        self._as_of_provider = as_of_provider or (lambda: datetime.now(UTC))

    def list_accounts(self) -> tuple[str, ...]:
        """Return account ids available from Robinhood."""
        return self._with_provider_errors(
            "list accounts",
            lambda: self._client_for_use().list_accounts(),
        )

    def get_portfolio(self, account_id: str) -> Portfolio:
        """Return a minimal provider-neutral portfolio for the account."""
        snapshot = self.get_snapshot(account_id)
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

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        """Return a point-in-time provider-neutral snapshot for the account."""
        normalized_account_id = account_id.strip()
        if not normalized_account_id:
            raise PortfolioAccountNotFoundError("portfolio account id is required")

        def load_snapshot() -> PortfolioSnapshot:
            client = self._client_for_use()
            accounts = client.list_accounts()
            resolved_account_id = normalized_account_id
            if normalized_account_id == "default" and accounts:
                resolved_account_id = accounts[0]
            elif normalized_account_id not in accounts:
                raise PortfolioAccountNotFoundError(
                    f"portfolio account not found: {normalized_account_id}"
                )
            raw_holdings = client.get_holdings(resolved_account_id)
            cash = client.get_cash(resolved_account_id)
            summary = client.get_account_summary(resolved_account_id)
            return _snapshot_from_payloads(
                account_id=resolved_account_id,
                as_of=self._as_of_provider(),
                raw_holdings=raw_holdings,
                raw_cash=cash,
                raw_summary=summary,
            )

        return self._with_provider_errors("get snapshot", load_snapshot)

    def _client_for_use(self) -> RobinhoodClient:
        if self._client is not None:
            return self._client
        if self._session_token is None and self._session_cache_path is None and (
            self._username is None or self._password is None
        ):
            raise PortfolioDataUnavailableError(
                "Robinhood portfolio provider requires credentials, a session token, "
                "or a local session cache from configuration/environment variables."
            )
        self._client = _RobinStocksReadOnlyClient(
            username=self._username,
            password=self._password,
            session_token=self._session_token,
            session_cache_path=self._session_cache_path,
        )
        return self._client

    def _with_provider_errors(self, operation: str, callback: Any) -> Any:
        try:
            return callback()
        except PortfolioProviderError:
            raise
        except Exception as error:
            message = str(error).lower()
            if "expired" in message or "unauthorized" in message or "login" in message:
                raise PortfolioDataUnavailableError(
                    f"Robinhood portfolio session unavailable during {operation}."
                ) from error
            raise PortfolioDataUnavailableError(
                f"Robinhood portfolio data unavailable during {operation}."
            ) from error


class _RobinStocksReadOnlyClient:
    """Tiny read-only wrapper around the optional robin_stocks package."""

    def __init__(
        self,
        *,
        username: str | None,
        password: str | None,
        session_token: str | None,
        session_cache_path: Path | None = None,
        module: ModuleType | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._session_token = session_token
        self._session_cache_path = session_cache_path
        self._rh = module
        self._logged_in = False

    def list_accounts(self) -> tuple[str, ...]:
        self._login()
        account = self._profiles().load_account_profile(info=None)
        account_number = _optional_text(_mapping(account).get("account_number"))
        return (account_number or "default",)

    def get_holdings(self, account_id: str) -> tuple[Mapping[str, Any], ...]:
        self._login()
        holdings = self._rh.account.build_holdings()
        return tuple(
            _holding_payload(symbol, payload)
            for symbol, payload in holdings.items()
        )

    def get_cash(self, account_id: str) -> Mapping[str, Any]:
        self._login()
        return _mapping(self._profiles().load_account_profile(info=None))

    def get_account_summary(self, account_id: str) -> Mapping[str, Any]:
        self._login()
        return _mapping(self._profiles().load_portfolio_profile(info=None))

    def _login(self) -> None:
        if self._logged_in:
            return
        if self._rh is None:
            self._rh = import_module("robin_stocks.robinhood")
        if self._session_token is not None:
            self._restore_session_token()
            self._logged_in = True
            return
        if self._session_cache_path is not None and self._session_cache_path.exists():
            try:
                self._restore_session_cache()
                self._logged_in = True
                return
            except Exception:
                self._logged_in = False
                if self._username is None or self._password is None:
                    raise
        self._rh.login(
            username=self._username,
            password=self._password,
            store_session=self._session_cache_path is not None,
            **self._session_cache_kwargs(),
        )
        self._logged_in = True

    def _profiles(self) -> Any:
        return self._rh.profiles

    def _restore_session_token(self) -> None:
        authentication = getattr(self._rh, "authentication", None)
        session = getattr(authentication, "SESSION", None)
        headers = getattr(session, "headers", None)
        if headers is None or not hasattr(headers, "update"):
            raise RuntimeError(
                "session token restore is unavailable in the installed Robinhood client"
            )
        headers.update({"Authorization": f"Bearer {self._session_token}"})

    def _restore_session_cache(self) -> None:
        if self._session_cache_path is None:
            raise RuntimeError("Robinhood session cache path is not configured")
        with self._session_cache_path.open("rb") as session_file:
            pickle_data = pickle.load(session_file)
        access_token = pickle_data["access_token"]
        token_type = pickle_data["token_type"]
        update_session = getattr(self._rh, "update_session")
        set_login_state = getattr(self._rh, "set_login_state")
        request_get = getattr(self._rh, "request_get")
        positions_url = getattr(self._rh, "positions_url")
        set_login_state(True)
        update_session("Authorization", f"{token_type} {access_token}")
        response = request_get(
            positions_url(),
            "pagination",
            {"nonzero": "true"},
            jsonify_data=False,
        )
        response.raise_for_status()

    def _session_cache_kwargs(self) -> dict[str, str]:
        if self._session_cache_path is None:
            return {}
        cache_dir, pickle_name = _robin_stocks_cache_location(
            self._session_cache_path
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        return {
            "pickle_path": str(cache_dir),
            "pickle_name": pickle_name,
        }


def _snapshot_from_payloads(
    *,
    account_id: str,
    as_of: datetime,
    raw_holdings: tuple[Mapping[str, Any], ...],
    raw_cash: Mapping[str, Any],
    raw_summary: Mapping[str, Any],
) -> PortfolioSnapshot:
    holdings = tuple(
        holding
        for holding in (_holding_from_payload(payload) for payload in raw_holdings)
        if holding is not None
    )
    cash_amount = _first_float(
        raw_cash,
        "cash",
        "cash_balance",
        "withdrawable_amount",
        "buying_power",
        "portfolio_cash",
    )
    cash_balances = (
        (PortfolioCashBalance(amount=cash_amount, currency="USD"),)
        if cash_amount is not None
        else ()
    )
    return PortfolioSnapshot(
        account_id=account_id,
        as_of=as_of,
        holdings=holdings,
        cash_balances=cash_balances,
        total_market_value=_first_float(
            raw_summary,
            "market_value",
            "total_market_value",
            "equity",
            "portfolio_value",
        ),
        total_cash=cash_amount,
        total_equity=_first_float(
            raw_summary,
            "total_equity",
            "equity",
            "portfolio_value",
            "extended_hours_equity",
        ),
        total_unrealized_gain_loss=_first_float(
            raw_summary,
            "total_unrealized_gain_loss",
            "unrealized_gain_loss",
        ),
    )


def _holding_from_payload(payload: Mapping[str, Any]) -> PortfolioHolding | None:
    symbol = _optional_text(
        _first_present(payload, "symbol", "ticker", "instrument_symbol")
    )
    if symbol is None:
        return None
    quantity = _first_float(payload, "quantity", "shares")
    if quantity is None or quantity == 0:
        return None
    market_value = _first_float(payload, "market_value", "equity", "value")
    current_price = _first_float(payload, "current_price", "price", "last_trade_price")
    if current_price is None and market_value is not None:
        current_price = market_value / quantity
    average_cost = _first_float(
        payload,
        "average_cost",
        "average_buy_price",
        "avg_cost",
    )
    if average_cost is None:
        average_cost = 0.0
    return PortfolioHolding(
        symbol=symbol,
        name=_optional_text(_first_present(payload, "name", "simple_name")) or symbol,
        quantity=quantity,
        average_cost=average_cost,
        current_price=current_price or 0.0,
        asset_type=_asset_type(payload),
        market_value=market_value,
        unrealized_gain_loss=_first_float(
            payload,
            "unrealized_gain_loss",
            "gain_loss",
        ),
        unrealized_gain_loss_percent=_first_float(
            payload,
            "unrealized_gain_loss_percent",
            "percentage",
        ),
        sector=_optional_text(payload.get("sector")),
        industry=_optional_text(payload.get("industry")),
        currency=_optional_text(payload.get("currency")) or "USD",
    )


def _asset_type(payload: Mapping[str, Any]) -> PortfolioAssetType:
    instrument_type = (
        _optional_text(_first_present(payload, "asset_type", "type", "instrument_type"))
        or "equity"
    ).lower()
    if "etf" in instrument_type:
        return PortfolioAssetType.ETF
    if "fund" in instrument_type:
        return PortfolioAssetType.MUTUAL_FUND
    if "crypto" in instrument_type:
        return PortfolioAssetType.CRYPTO
    return PortfolioAssetType.EQUITY


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value
    return None


def _first_float(payload: Mapping[str, Any], *keys: str) -> float | None:
    return _optional_float(_first_present(payload, *keys))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(float_value):
        return None
    return float_value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_secret(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _normalize_cache_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if str(path).strip() == "":
        return None
    return path


def _robin_stocks_cache_location(cache_path: Path) -> tuple[Path, str]:
    """Translate a ParakeetNest cache file path to robin-stocks cache arguments."""
    if cache_path.name == "robinhood.pickle":
        return cache_path.parent, ""
    if cache_path.name.startswith("robinhood") and cache_path.suffix == ".pickle":
        pickle_name = cache_path.name.removeprefix("robinhood").removesuffix(".pickle")
        return cache_path.parent, pickle_name
    return cache_path.parent, f"_{cache_path.stem}"


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _holding_payload(symbol: str, payload: Any) -> Mapping[str, Any]:
    raw_payload = dict(_mapping(payload))
    raw_payload.setdefault("symbol", symbol)
    return raw_payload


__all__ = ["RobinhoodClient", "RobinhoodPortfolioProvider"]
