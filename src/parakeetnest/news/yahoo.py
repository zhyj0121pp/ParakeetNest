"""Yahoo Finance-backed news provider."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
import logging
import time
from types import ModuleType
from typing import Any, Callable, TypeVar

from parakeetnest.market_data.errors import (
    MalformedMarketDataError,
    MarketDataError,
    ProviderUnavailableError,
    RateLimitError,
)
from parakeetnest.market_data.models import Symbol
from parakeetnest.news.models import NewsArticle, NewsQuery


_T = TypeVar("_T")
logger = logging.getLogger(__name__)


class YahooFinanceNewsProvider:
    """News provider backed by Yahoo Finance through yfinance."""

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

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        """Return Yahoo Finance news mapped to provider-neutral articles."""
        try:
            payloads = self._with_retries(
                "get_news",
                tuple(query.symbols or ()),
                lambda: self._load_news_payloads(query),
            )
            articles: list[NewsArticle] = []
            for payload, fallback_symbols in payloads:
                article = self._article_from_payload(payload, fallback_symbols)
                if self._matches_query(article, query):
                    articles.append(article)
                if len(articles) >= query.limit:
                    break
            return articles
        except MarketDataError as error:
            self._log_failure("get_news", tuple(query.symbols or ()), error)
            raise
        except Exception as error:
            mapped = MalformedMarketDataError(
                "Yahoo Finance returned malformed news data.",
                cause=error,
            )
            self._log_failure("get_news", tuple(query.symbols or ()), mapped)
            raise mapped from error

    def _load_news_payloads(
        self,
        query: NewsQuery,
    ) -> list[tuple[dict[str, Any], list[str] | None]]:
        payloads: list[tuple[dict[str, Any], list[str] | None]] = []

        if query.symbols:
            for symbol in query.symbols:
                ticker = self._ticker(symbol)
                raw_news = self._ticker_news(ticker, query.limit)
                payloads.extend(
                    (payload, [symbol]) for payload in self._news_items(raw_news, symbol)
                )
            return payloads

        if query.keywords:
            raw_news = self._keyword_news(query.keywords)
            return [(payload, None) for payload in self._news_items(raw_news, None)]

        return []

    @staticmethod
    def _ticker_news(ticker: Any, limit: int) -> Any:
        get_news = getattr(ticker, "get_news", None)
        if callable(get_news):
            return get_news(count=limit, tab="news")
        return getattr(ticker, "news", [])

    def _ticker(self, symbol: str) -> Any:
        return self._yfinance().Ticker(symbol)

    def _keyword_news(self, keywords: list[str]) -> Any:
        yfinance = self._yfinance()
        if not hasattr(yfinance, "Search"):
            return []
        search = yfinance.Search(" ".join(keywords))
        return getattr(search, "news", [])

    def _yfinance(self) -> ModuleType:
        if self._yf is None:
            self._yf = import_module("yfinance")
        return self._yf

    def _news_items(
        self,
        payload: Any,
        symbol: str | None,
    ) -> list[dict[str, Any]]:
        if payload is None:
            return []
        if not isinstance(payload, list | tuple):
            raise MalformedMarketDataError(
                "Yahoo Finance returned a non-list news payload.",
                symbol=Symbol(symbol) if symbol else None,
            )

        items: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise MalformedMarketDataError(
                    "Yahoo Finance returned a non-mapping news item.",
                    symbol=Symbol(symbol) if symbol else None,
                )
            items.append(item)
        return items

    def _article_from_payload(
        self,
        payload: dict[str, Any],
        fallback_symbols: list[str] | None,
    ) -> NewsArticle:
        content = self._mapping(payload.get("content"))
        title = self._required_str(
            self._first_present(payload, content, "title"),
            "title",
        )
        url = self._required_str(
            self._first_present(
                payload,
                content,
                "link",
                "url",
                "canonicalUrl",
                "clickThroughUrl",
            ),
            "url",
        )
        source = self._source(payload, content)
        published_at = self._published_at(
            self._first_present(
                payload,
                content,
                "providerPublishTime",
                "pubDate",
                "displayTime",
            )
        )
        symbols = self._symbols(payload, content, fallback_symbols)

        return NewsArticle(
            title=title,
            url=url,
            source=source,
            published_at=published_at,
            summary=self._optional_str(
                self._first_present(payload, content, "summary", "description")
            ),
            symbols=symbols,
            provider=self.provider_name,
        )

    def _mapping(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
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

    def _required_str(self, value: Any, field_name: str) -> str:
        parsed = self._optional_str(value)
        if parsed is None:
            raise MalformedMarketDataError(
                f"Yahoo Finance returned a news item without {field_name}."
            )
        return parsed

    def _optional_str(self, value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("url", "href", "displayName"):
                parsed = self._optional_str(value.get(key))
                if parsed is not None:
                    return parsed
            return None
        if value is None:
            return None
        parsed = str(value).strip()
        return parsed or None

    def _source(self, payload: dict[str, Any], content: dict[str, Any]) -> str:
        provider = self._mapping(self._first_present(payload, content, "provider"))
        return (
            self._optional_str(payload.get("publisher"))
            or self._optional_str(provider.get("displayName"))
            or self._optional_str(provider.get("name"))
            or "Yahoo Finance"
        )

    def _published_at(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        if isinstance(value, int | float):
            return datetime.fromtimestamp(value, tz=UTC)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
                    UTC
                )
            except ValueError as error:
                raise MalformedMarketDataError(
                    "Yahoo Finance returned an invalid news publication time.",
                    details=value,
                    cause=error,
                ) from error
        raise MalformedMarketDataError(
            "Yahoo Finance returned a news item without published_at."
        )

    def _symbols(
        self,
        payload: dict[str, Any],
        content: dict[str, Any],
        fallback_symbols: list[str] | None,
    ) -> list[str] | None:
        raw_symbols = (
            payload.get("relatedTickers")
            or payload.get("symbols")
            or content.get("relatedTickers")
            or content.get("symbols")
        )
        finance = self._mapping(content.get("finance"))
        raw_symbols = raw_symbols or finance.get("stockTickers")
        if raw_symbols is None:
            return fallback_symbols
        if not isinstance(raw_symbols, list | tuple):
            return fallback_symbols
        symbols = [
            symbol
            for symbol in (self._symbol_value(raw_symbol) for raw_symbol in raw_symbols)
            if symbol is not None
        ]
        return symbols or fallback_symbols

    def _symbol_value(self, value: Any) -> str | None:
        if isinstance(value, dict):
            return self._optional_str(value.get("symbol"))
        return self._optional_str(value)

    def _matches_keywords(
        self,
        article: NewsArticle,
        keywords: list[str] | None,
    ) -> bool:
        if not keywords:
            return True
        searchable_text = " ".join(
            value
            for value in (article.title, article.summary, article.source)
            if value is not None
        ).casefold()
        return all(keyword.casefold() in searchable_text for keyword in keywords)

    def _matches_query(self, article: NewsArticle, query: NewsQuery) -> bool:
        if not self._matches_keywords(article, query.keywords):
            return False
        if (
            query.published_after is not None
            and article.published_at < query.published_after
        ):
            return False
        return not (
            query.published_before is not None
            and article.published_at > query.published_before
        )

    def _with_retries(
        self,
        operation: str,
        symbols: tuple[str, ...],
        call: Callable[[], _T],
    ) -> _T:
        last_error: ProviderUnavailableError | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return call()
            except MarketDataError:
                raise
            except Exception as error:
                mapped = self._map_provider_exception(error)
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

    def _map_provider_exception(self, error: Exception) -> MarketDataError:
        error_type = type(error).__name__.lower()
        error_module = type(error).__module__.lower()
        error_message = str(error).lower()
        root_cause = str(error) or type(error).__name__
        if "rate" in error_message and "limit" in error_message:
            return RateLimitError(
                "Yahoo Finance rate limit reached.",
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
                details=root_cause,
                cause=error,
            )
        return ProviderUnavailableError(
            "Yahoo Finance provider failed unexpectedly.",
            details=root_cause,
            cause=error,
            retryable=False,
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
        symbols: tuple[str, ...],
        error: MarketDataError,
        *,
        attempt: int | None = None,
    ) -> None:
        symbol_text = ",".join(symbols) if symbols else "none"
        root_cause = error.details or str(error.cause) or error.message
        extra = f" attempt={attempt}/{self._max_attempts}" if attempt is not None else ""
        logger.warning(
            "news provider failure provider=%s operation=%s symbols=%s root_cause=%s%s",
            self.provider_name,
            operation,
            symbol_text,
            root_cause,
            extra,
        )


__all__ = ["YahooFinanceNewsProvider"]
