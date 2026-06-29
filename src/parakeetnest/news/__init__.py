"""Provider-agnostic News Layer interfaces and domain models."""

from parakeetnest.news.mock import MockNewsProvider
from parakeetnest.news.models import NewsArticle, NewsQuery
from parakeetnest.news.provider import NewsProvider
from parakeetnest.news.registry import (
    NewsProviderRegistration,
    NewsProviderRegistry,
    create_news_provider_registry,
)
from parakeetnest.news.service import NewsService

__all__ = [
    "MockNewsProvider",
    "NewsArticle",
    "NewsProvider",
    "NewsProviderRegistration",
    "NewsProviderRegistry",
    "NewsQuery",
    "NewsService",
    "create_news_provider_registry",
]
