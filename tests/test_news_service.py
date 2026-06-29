"""Tests for the provider-agnostic news service."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.news import MockNewsProvider, NewsArticle, NewsProvider, NewsQuery
from parakeetnest.news import NewsService


class SpyNewsProvider:
    """Provider test double that records news service delegation."""

    def __init__(self) -> None:
        self.calls: list[NewsQuery] = []
        self.articles = [
            NewsArticle(
                title="AMD expands AI accelerator roadmap",
                url="https://example.com/news/amd-ai-roadmap",
                source="Parakeet Wire",
                published_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
                summary="AMD outlined new data center accelerator milestones.",
                symbols=["AMD"],
                provider="spy",
            )
        ]

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        """Record and return provider-backed articles."""
        self.calls.append(query)
        return self.articles


def test_get_news_delegates_to_provider_once() -> None:
    """The service should make exactly one provider call for news."""
    provider = SpyNewsProvider()
    service = NewsService(provider)
    query = NewsQuery(symbols=["amd"])

    service.get_news(query)

    assert provider.calls == [query]


def test_get_news_returns_exact_provider_result() -> None:
    """The service should return the provider-owned result unchanged."""
    provider = SpyNewsProvider()
    service = NewsService(provider)

    articles = service.get_news(NewsQuery())

    assert articles is provider.articles


def test_service_works_with_mock_news_provider() -> None:
    """The concrete mock provider should be usable through the service."""
    provider: NewsProvider = MockNewsProvider()
    service = NewsService(provider)

    articles = service.get_news(NewsQuery(symbols=["MSFT"]))

    assert len(articles) == 1
    assert articles[0].title == "Nvidia and Microsoft deepen cloud AI collaboration"


def test_service_does_not_modify_provider_result() -> None:
    """The service should not copy, sort, filter, or otherwise mutate results."""
    provider = SpyNewsProvider()
    service = NewsService(provider)
    expected_result = provider.articles
    expected_articles = list(provider.articles)

    articles = service.get_news(NewsQuery(keywords=["AI"]))

    assert articles is expected_result
    assert provider.articles == expected_articles
