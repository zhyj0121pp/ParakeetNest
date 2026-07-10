"""News context provider backed by the News Layer service boundary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    NewsContext,
    NewsItem,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.news.models import NewsArticle, NewsQuery
from parakeetnest.news.service import NewsService


class NewsContextProvider:
    """Build news context from provider-backed NewsService articles."""

    provider_name = "news"

    def __init__(
        self,
        news_service: NewsService,
        *,
        per_symbol_limit: int = 5,
        preferred_lookback_days: int = 3,
        fallback_lookback_days: int = 7,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._news_service = news_service
        self._per_symbol_limit = max(1, per_symbol_limit)
        self._preferred_lookback_days = max(1, preferred_lookback_days)
        self._fallback_lookback_days = max(
            self._preferred_lookback_days,
            fallback_lookback_days,
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        as_of = request.as_of or self._clock()
        articles: list[NewsArticle] = []
        errors: list[str] = []
        for symbol in request.symbols:
            try:
                articles.extend(self._articles_for_symbol(symbol, as_of=as_of))
            except Exception as exc:  # Keep other ticker news available.
                errors.append(f"{symbol}: {exc}")
        normalized_articles = tuple(self._deduplicate(articles))
        fetched_at = request.as_of or max(
            (article.published_at for article in normalized_articles),
            default=None,
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            news=NewsContext(
                source=self.provider_name,
                fetched_at=fetched_at,
                items=tuple(
                    self._item_for(article, request)
                    for article in normalized_articles
                ),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "news_service"},
            errors=tuple(errors),
        )

    def _articles_for_symbol(
        self,
        symbol: str,
        *,
        as_of: datetime,
    ) -> tuple[NewsArticle, ...]:
        fallback_start = as_of - timedelta(days=self._fallback_lookback_days)
        candidates = self._news_service.get_news(
            NewsQuery(
                symbols=[symbol],
                limit=max(10, self._per_symbol_limit),
                published_after=fallback_start,
                published_before=as_of,
            )
        )
        preferred_start = as_of - timedelta(days=self._preferred_lookback_days)
        preferred = tuple(
            article
            for article in candidates
            if article.published_at >= preferred_start
        )
        selected = preferred or tuple(candidates)
        return tuple(
            sorted(selected, key=lambda article: article.published_at, reverse=True)[
                : self._per_symbol_limit
            ]
        )

    @staticmethod
    def _deduplicate(articles: list[NewsArticle]) -> tuple[NewsArticle, ...]:
        seen: set[tuple[str, str]] = set()
        unique: list[NewsArticle] = []
        for article in articles:
            identity = (article.url.strip(), article.title.strip().casefold())
            if identity in seen:
                continue
            seen.add(identity)
            unique.append(article)
        return tuple(unique)

    def _item_for(self, article: NewsArticle, request: ContextRequest) -> NewsItem:
        return NewsItem(
            title=article.title,
            source=article.source,
            symbol=self._context_symbol(article, request),
            url=article.url,
            summary=article.summary,
            published_at=article.published_at,
        )

    @staticmethod
    def _context_symbol(
        article: NewsArticle,
        request: ContextRequest,
    ) -> str | None:
        if not article.symbols:
            return None

        requested_symbols = set(request.symbols)
        for symbol in article.symbols:
            if symbol in requested_symbols:
                return symbol
        return article.symbols[0]
