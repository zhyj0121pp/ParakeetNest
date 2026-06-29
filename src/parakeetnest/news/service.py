"""Provider-agnostic news service boundary."""

from __future__ import annotations

from parakeetnest.news.models import NewsArticle, NewsQuery
from parakeetnest.news.provider import NewsProvider


class NewsService:
    """Single entry point for provider-backed news requests."""

    def __init__(self, provider: NewsProvider) -> None:
        """Initialize the service with one news provider."""
        self._provider = provider

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        """Return provider-backed news articles for the query."""
        return self._provider.get_news(query)


__all__ = ["NewsService"]
