"""Provider contract for news integrations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from parakeetnest.news.models import NewsArticle, NewsQuery


@runtime_checkable
class NewsProvider(Protocol):
    """Small contract that all news providers must implement."""

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        """Return provider-neutral news articles for the query."""
        ...


__all__ = ["NewsProvider"]
