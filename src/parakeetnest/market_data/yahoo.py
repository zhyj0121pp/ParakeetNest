"""Yahoo Finance-backed market data provider."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from importlib import import_module
from math import isfinite
from types import ModuleType
from typing import Any

from parakeetnest.market_data.models import (
    AssetType,
    MarketDataRange,
    MarketDataSnapshot,
    PriceBar,
    Symbol,
)
from parakeetnest.market_data.provider import ProviderError


class YahooFinanceMarketDataProvider:
    """Market data provider backed by Yahoo Finance through yfinance."""

    def __init__(self, yfinance_module: ModuleType | None = None) -> None:
        """Initialize the provider, optionally with an injected yfinance module."""
        self._yf = yfinance_module

    def supports(self, symbol: Symbol) -> bool:
        """Return whether the symbol is syntactically usable with Yahoo Finance."""
        return bool(symbol.ticker)

    def get_quote(self, symbol: Symbol | str) -> MarketDataSnapshot:
        """Return the latest quote for one symbol."""
        normalized_symbol = self._normalize_symbol(symbol)
        ticker = self._ticker(normalized_symbol)
        fast_info = self._mapping_from(getattr(ticker, "fast_info", {}))
        info = self._mapping_from(getattr(ticker, "info", {}))

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

    def get_quotes(self, symbols: Iterable[Symbol | str]) -> list[MarketDataSnapshot]:
        """Return latest quotes for multiple symbols."""
        return [self.get_quote(symbol) for symbol in symbols]

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        """Return current point-in-time market data for the symbol."""
        return self.get_quote(symbol)

    def get_price_history(
        self,
        symbol: Symbol,
        range: MarketDataRange,
    ) -> list[PriceBar]:
        """Return historical price bars for the symbol and requested range."""
        ticker = self._ticker(symbol)
        kwargs: dict[str, Any] = {}
        if range.period is not None:
            kwargs["period"] = range.period
        if range.interval is not None:
            kwargs["interval"] = range.interval
        if range.start is not None:
            kwargs["start"] = range.start
        if range.end is not None:
            kwargs["end"] = range.end

        history = ticker.history(**kwargs)
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
        return bars

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

    def _mapping_from(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "items"):
            return dict(value.items())
        return {}

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
            raise ProviderError(
                f"Yahoo Finance returned no usable {field_name} for {symbol.ticker}"
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
        raise ProviderError("Yahoo Finance returned a price bar without a timestamp")


__all__ = ["YahooFinanceMarketDataProvider"]
