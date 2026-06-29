"""News context provider backed by the News Layer service boundary."""

from __future__ import annotations

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

    def __init__(self, news_service: NewsService) -> None:
        self._news_service = news_service

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        articles = tuple(
            self._news_service.get_news(NewsQuery(symbols=list(request.symbols)))
        )
        fetched_at = request.as_of or max(
            (article.published_at for article in articles),
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
                items=tuple(self._item_for(article, request) for article in articles),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "news_service"},
        )

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
