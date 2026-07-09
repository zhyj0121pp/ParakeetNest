"""Yahoo Finance-backed market data provider."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from importlib import import_module
import logging
from math import isfinite
import time
from types import ModuleType
from typing import Any, Callable, TypeVar

from parakeetnest.market_data.errors import (
    InvalidSymbolError,
    MalformedMarketDataError,
    MarketDataError,
    ProviderUnavailableError,
    RateLimitError,
)
from parakeetnest.market_data.models import (
    AssetType,
    CompanyInfo,
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    Symbol,
)


_T = TypeVar("_T")
logger = logging.getLogger(__name__)


class YahooFinanceMarketDataProvider:
    """Market data provider backed by Yahoo Finance through yfinance."""

    provider_name = "yahoo"

    def __init__(
        self,
        yfinance_module: ModuleType | None = None,
        *,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.1,
    ) -> None:
        """Initialize the provider, optionally with an injected yfinance module."""
        self._yf = yfinance_module
        self._max_attempts = max(1, max_attempts)
        self._retry_delay_seconds = max(0.0, retry_delay_seconds)

    def supports(self, symbol: Symbol) -> bool:
        """Return whether the symbol is syntactically usable with Yahoo Finance."""
        return bool(symbol.ticker)

    def get_quote(self, symbol: Symbol | str) -> MarketDataSnapshot:
        """Return the latest quote for one symbol."""
        normalized_symbol = self._normalize_symbol(symbol)
        self._raise_if_invalid_symbol(normalized_symbol)
        try:
            raw_fast_info, raw_info = self._with_retries(
                "get_quote",
                (normalized_symbol,),
                lambda: self._load_quote_payload(normalized_symbol),
            )
            fast_info = self._mapping_from(raw_fast_info)
            info = self._mapping_from(raw_info)
            if not fast_info and not info:
                raise MalformedMarketDataError(
                    f"Yahoo Finance returned an empty response for {normalized_symbol.ticker}",
                    symbol=normalized_symbol,
                    details="empty_response",
                )

            price = self._required_float(
                self._first_present(
                    fast_info,
                    info,
                    "last_price",
                    "lastPrice",
                    "regularMarketPrice",
                    "currentPrice",
                    "previousClose",
                ),
                normalized_symbol,
                "price",
            )

            return MarketDataSnapshot(
                symbol=normalized_symbol,
                asset_type=self._asset_type(info),
                price=price,
                currency=str(
                    self._first_present(fast_info, info, "currency", "financialCurrency")
                    or "USD"
                ),
                timestamp=self._timestamp(fast_info, info),
                previous_close=self._optional_float(
                    self._first_present(
                        fast_info,
                        info,
                        "previous_close",
                        "previousClose",
                        "regularMarketPreviousClose",
                    )
                ),
                open=self._optional_float(
                    self._first_present(fast_info, info, "open", "regularMarketOpen")
                ),
                high=self._optional_float(
                    self._first_present(
                        fast_info,
                        info,
                        "day_high",
                        "dayHigh",
                        "regularMarketDayHigh",
                    )
                ),
                low=self._optional_float(
                    self._first_present(
                        fast_info,
                        info,
                        "day_low",
                        "dayLow",
                        "regularMarketDayLow",
                    )
                ),
                volume=self._optional_float(
                    self._first_present(fast_info, info, "last_volume", "volume")
                ),
            )
        except MarketDataError as error:
            self._log_failure("get_quote", (normalized_symbol,), error)
            raise
        except Exception as error:
            mapped = MalformedMarketDataError(
                f"Yahoo Finance returned malformed quote data for {normalized_symbol.ticker}",
                symbol=normalized_symbol,
                cause=error,
            )
            self._log_failure("get_quote", (normalized_symbol,), mapped)
            raise mapped from error

    def get_quotes(self, symbols: Iterable[Symbol | str]) -> list[MarketDataSnapshot]:
        """Return latest quotes for multiple symbols."""
        return [self.get_quote(symbol) for symbol in symbols]

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Return current point-in-time market data for the symbol."""
        return self.get_quote(symbol)

    def get_company_info(self, symbol: Symbol | str) -> CompanyInfo:
        """Return basic provider-neutral company profile information."""
        normalized_symbol = self._normalize_symbol(symbol)
        self._raise_if_invalid_symbol(normalized_symbol)
        try:
            raw_info = self._with_retries(
                "get_company_info",
                (normalized_symbol,),
                lambda: getattr(self._ticker(normalized_symbol), "info", {}),
            )
            info = self._mapping_from(raw_info)
            if not info:
                raise MalformedMarketDataError(
                    f"Yahoo Finance returned an empty company info response for {normalized_symbol.ticker}",
                    symbol=normalized_symbol,
                    details="empty_response",
                )

            name = self._optional_string(
                self._first_present(
                    {},
                    info,
                    "longName",
                    "shortName",
                    "displayName",
                    "symbol",
                )
            )
            if name is None:
                raise MalformedMarketDataError(
                    f"Yahoo Finance returned no usable company name for {normalized_symbol.ticker}",
                    symbol=normalized_symbol,
                )

            enterprise_value = self._optional_float(info.get("enterpriseValue"))
            revenue_ttm = self._optional_float(
                self._first_present({}, info, "totalRevenue", "revenueTTM")
            )
            ev_to_sales = self._optional_float(
                self._first_present(
                    {},
                    info,
                    "enterpriseToRevenue",
                    "enterpriseToSales",
                    "evToSales",
                )
            )
            if ev_to_sales is None and enterprise_value is not None and revenue_ttm:
                ev_to_sales = enterprise_value / revenue_ttm

            return CompanyInfo(
                symbol=normalized_symbol,
                name=name,
                asset_type=self._asset_type(info),
                exchange=self._optional_string(
                    self._first_present({}, info, "exchange", "fullExchangeName")
                ),
                currency=self._optional_string(
                    self._first_present({}, info, "currency", "financialCurrency")
                ),
                sector=self._optional_string(info.get("sector")),
                industry=self._optional_string(info.get("industry")),
                country=self._optional_string(info.get("country")),
                website=self._optional_string(info.get("website")),
                market_cap=self._optional_float(info.get("marketCap")),
                beta=self._optional_float(info.get("beta")),
                trailing_pe=self._optional_float(info.get("trailingPE")),
                forward_pe=self._optional_float(info.get("forwardPE")),
                enterprise_value=enterprise_value,
                revenue_ttm=revenue_ttm,
                ev_to_sales=ev_to_sales,
                full_time_employees=self._optional_int(info.get("fullTimeEmployees")),
                summary=self._optional_string(
                    self._first_present({}, info, "longBusinessSummary", "description")
                ),
            )
        except MarketDataError as error:
            self._log_failure("get_company_info", (normalized_symbol,), error)
            raise
        except Exception as error:
            mapped = MalformedMarketDataError(
                f"Yahoo Finance returned malformed company info for {normalized_symbol.ticker}",
                symbol=normalized_symbol,
                cause=error,
            )
            self._log_failure("get_company_info", (normalized_symbol,), mapped)
            raise mapped from error

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        """Return historical price bars for the symbol and requested range."""
        self._raise_if_invalid_symbol(symbol)
        kwargs: dict[str, Any] = {}
        if range.period is not None:
            kwargs["period"] = range.period
        if range.interval is not None:
            kwargs["interval"] = range.interval
        if range.start is not None:
            kwargs["start"] = range.start
        if range.end is not None:
            kwargs["end"] = range.end

        try:
            history = self._with_retries(
                "get_price_history",
                (symbol,),
                lambda: self._ticker(symbol).history(**kwargs),
            )
            bars: list[PriceBar] = []
            for row_time, row in self._history_rows(history):
                bars.append(
                    PriceBar(
                        symbol=symbol,
                        start_time=self._row_timestamp(row_time),
                        open=self._required_float(row["Open"], symbol, "open"),
                        high=self._required_float(row["High"], symbol, "high"),
                        low=self._required_float(row["Low"], symbol, "low"),
                        close=self._required_float(row["Close"], symbol, "close"),
                        volume=self._optional_float(row.get("Volume")),
                    )
                )
            if not bars:
                raise MalformedMarketDataError(
                    f"Yahoo Finance returned an empty history response for {symbol.ticker}",
                    symbol=symbol,
                    details="empty_response",
                )
            return bars
        except MarketDataError as error:
            self._log_failure("get_price_history", (symbol,), error)
            raise
        except Exception as error:
            mapped = MalformedMarketDataError(
                f"Yahoo Finance returned malformed history data for {symbol.ticker}",
                symbol=symbol,
                cause=error,
            )
            self._log_failure("get_price_history", (symbol,), mapped)
            raise mapped from error

    def _ticker(self, symbol: Symbol) -> Any:
        return self._yfinance().Ticker(symbol.ticker)

    def _yfinance(self) -> ModuleType:
        if self._yf is None:
            self._yf = import_module("yfinance")
        return self._yf

    def _normalize_symbol(self, symbol: Symbol | str) -> Symbol:
        if isinstance(symbol, Symbol):
            return symbol
        return Symbol(symbol)

    def _raise_if_invalid_symbol(self, symbol: Symbol) -> None:
        if not symbol.ticker:
            raise InvalidSymbolError("Symbol must not be empty.", symbol=symbol)

    def _load_quote_payload(self, symbol: Symbol) -> tuple[Any, Any]:
        ticker = self._ticker(symbol)
        return (getattr(ticker, "fast_info", {}), getattr(ticker, "info", {}))

    def _with_retries(
        self,
        operation: str,
        symbols: tuple[Symbol, ...],
        call: Callable[[], _T],
    ) -> _T:
        last_error: ProviderUnavailableError | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return call()
            except MarketDataError:
                raise
            except Exception as error:
                mapped = self._map_provider_exception(error, symbols[0])
                if (
                    not isinstance(mapped, ProviderUnavailableError)
                    or not mapped.retryable
                ):
                    self._log_failure(operation, symbols, mapped)
                    raise mapped from error
                last_error = mapped
                self._log_failure(operation, symbols, mapped, attempt=attempt)
                if attempt == self._max_attempts:
                    raise mapped from error
                if self._retry_delay_seconds:
                    time.sleep(self._retry_delay_seconds)
        assert last_error is not None
        raise last_error

    def _map_provider_exception(
        self,
        error: Exception,
        symbol: Symbol,
    ) -> MarketDataError:
        error_type = type(error).__name__.lower()
        error_module = type(error).__module__.lower()
        error_message = str(error).lower()
        root_cause = str(error) or type(error).__name__
        if self._looks_like_invalid_symbol(error_type, error_message):
            return InvalidSymbolError(
                f"Yahoo Finance could not find symbol {symbol.ticker}",
                symbol=symbol,
                details=root_cause,
                cause=error,
            )
        if "rate" in error_message and "limit" in error_message:
            return RateLimitError(
                "Yahoo Finance rate limit reached.",
                symbol=symbol,
                details=root_cause,
                cause=error,
            )
        if self._looks_like_transient_failure(
            error,
            error_type,
            error_module,
            error_message,
        ):
            return ProviderUnavailableError(
                "Yahoo Finance is temporarily unavailable.",
                symbol=symbol,
                details=root_cause,
                cause=error,
            )
        return ProviderUnavailableError(
            "Yahoo Finance provider failed unexpectedly.",
            symbol=symbol,
            details=root_cause,
            cause=error,
            retryable=False,
        )

    def _looks_like_invalid_symbol(self, error_type: str, error_message: str) -> bool:
        invalid_markers = (
            "invalid",
            "not found",
            "no timezone found",
            "possibly delisted",
            "symbol may be delisted",
            "no data found",
        )
        return "invalid" in error_type or any(
            marker in error_message for marker in invalid_markers
        )

    def _looks_like_transient_failure(
        self,
        error: Exception,
        error_type: str,
        error_module: str,
        error_message: str,
    ) -> bool:
        if isinstance(error, TimeoutError):
            return True
        if "timeout" in error_type or "timed out" in error_message:
            return True
        network_modules = ("requests", "urllib3", "socket", "http.client", "httpcore")
        if any(module in error_module for module in network_modules):
            return True
        network_markers = (
            "connection",
            "network",
            "temporarily unavailable",
            "temporary failure",
            "service unavailable",
            "connection reset",
            "connection aborted",
            "remote end closed",
        )
        return isinstance(error, OSError) or any(
            marker in error_message for marker in network_markers
        )

    def _log_failure(
        self,
        operation: str,
        symbols: tuple[Symbol, ...],
        error: MarketDataError,
        *,
        attempt: int | None = None,
    ) -> None:
        symbol_text = ",".join(symbol.ticker for symbol in symbols)
        root_cause = error.details or str(error.cause) or error.message
        extra = f" attempt={attempt}/{self._max_attempts}" if attempt is not None else ""
        logger.warning(
            "market data provider failure provider=%s operation=%s symbols=%s root_cause=%s%s",
            self.provider_name,
            operation,
            symbol_text,
            root_cause,
            extra,
        )

    def _mapping_from(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "items"):
            return dict(value.items())
        raise MalformedMarketDataError("Yahoo Finance returned a non-mapping payload.")

    def _first_present(
        self,
        primary: dict[str, Any],
        secondary: dict[str, Any],
        *keys: str,
    ) -> Any:
        for key in keys:
            if key in primary and primary[key] is not None:
                return primary[key]
            if key in secondary and secondary[key] is not None:
                return secondary[key]
        return None

    def _required_float(self, value: Any, symbol: Symbol, field_name: str) -> float:
        parsed = self._optional_float(value)
        if parsed is None:
            raise MalformedMarketDataError(
                f"Yahoo Finance returned no usable {field_name} for {symbol.ticker}",
                symbol=symbol,
            )
        return parsed

    def _optional_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(parsed):
            return None
        return parsed

    def _optional_int(self, value: Any) -> int | None:
        parsed = self._optional_float(value)
        if parsed is None:
            return None
        return int(parsed)

    def _optional_string(self, value: Any) -> str | None:
        if value is None:
            return None
        parsed = str(value).strip()
        return parsed or None

    def _timestamp(
        self,
        fast_info: dict[str, Any],
        info: dict[str, Any],
    ) -> datetime:
        raw_timestamp = self._first_present(
            fast_info,
            info,
            "regular_market_time",
            "regularMarketTime",
        )
        if isinstance(raw_timestamp, datetime):
            if raw_timestamp.tzinfo is None:
                return raw_timestamp.replace(tzinfo=UTC)
            return raw_timestamp.astimezone(UTC)
        if isinstance(raw_timestamp, int | float):
            return datetime.fromtimestamp(raw_timestamp, tz=UTC)
        return datetime.now(UTC)

    def _asset_type(self, info: dict[str, Any]) -> AssetType:
        quote_type = str(info.get("quoteType", "")).lower()
        if quote_type in {"equity", "stock"}:
            return AssetType.STOCK
        if quote_type == "etf":
            return AssetType.ETF
        if quote_type in {"index", "mutualfund"}:
            return AssetType.INDEX
        if quote_type in {"cryptocurrency", "crypto"}:
            return AssetType.CRYPTO
        return AssetType.UNKNOWN

    def _history_rows(self, history: Any) -> Iterable[tuple[Any, Any]]:
        if hasattr(history, "iterrows"):
            return history.iterrows()
        return []

    def _row_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        if hasattr(value, "to_pydatetime"):
            timestamp = value.to_pydatetime()
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=UTC)
            return timestamp.astimezone(UTC)
        raise MalformedMarketDataError(
            "Yahoo Finance returned a price bar without a timestamp"
        )


__all__ = ["YahooFinanceMarketDataProvider"]
