"""Tests for NewsContextProvider service-backed behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.context import ContextRequest, UnsupportedContextRequestError
from parakeetnest.context.providers import NewsContextProvider
from parakeetnest.news import NewsArticle, NewsQuery


class RecordingNewsService:
    """News service test double that records provider-neutral queries."""

    def __init__(self, articles: list[NewsArticle]) -> None:
        self.articles = articles
        self.queries: list[NewsQuery] = []

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        self.queries.append(query)
        return self.articles


def test_news_context_provider_builds_news_context_from_news_service() -> None:
    published_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    service = RecordingNewsService(
        [
            NewsArticle(
                title="AMD expands AI accelerator roadmap",
                url="https://example.com/news/amd-ai-roadmap",
                source="Parakeet Wire",
                published_at=published_at,
                summary="AMD outlined new accelerator milestones.",
                symbols=["AMD"],
                provider="mock",
            )
        ]
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = NewsContextProvider(service).build_context(request)

    assert service.queries == [NewsQuery(symbols=["AMD"])]
    assert result.provider_name == "news"
    assert result.metadata == {"source": "news_service"}
    assert result.partial_context.news is not None
    assert result.partial_context.news.source == "news"
    assert result.partial_context.news.fetched_at == published_at
    assert result.partial_context.news.items[0].title == (
        "AMD expands AI accelerator roadmap"
    )
    assert result.partial_context.news.items[0].source == "Parakeet Wire"
    assert result.partial_context.news.items[0].symbol == "AMD"


def test_news_context_provider_preserves_empty_news_result() -> None:
    service = RecordingNewsService([])
    as_of = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    request = ContextRequest(
        question="Review POET.",
        symbols=("POET",),
        as_of=as_of,
    )

    result = NewsContextProvider(service).build_context(request)

    assert service.queries == [NewsQuery(symbols=["POET"])]
    assert result.partial_context.news is not None
    assert result.partial_context.news.items == ()
    assert result.partial_context.news.fetched_at == as_of


def test_news_context_provider_rejects_requests_without_symbols() -> None:
    service = RecordingNewsService([])
    provider = NewsContextProvider(service)
    request = ContextRequest(question="Review the market.", symbols=())

    with pytest.raises(UnsupportedContextRequestError):
        provider.build_context(request)

    assert service.queries == []
