"""Tests for NewsContextProvider service-backed behavior."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

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
        articles = self.articles
        if query.symbols:
            symbols = set(query.symbols)
            articles = [
                article
                for article in articles
                if article.symbols and symbols.intersection(article.symbols)
            ]
        if query.published_after is not None:
            articles = [
                article
                for article in articles
                if article.published_at >= query.published_after
            ]
        if query.published_before is not None:
            articles = [
                article
                for article in articles
                if article.published_at <= query.published_before
            ]
        return articles[: query.limit]


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
    as_of = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    request = ContextRequest(question="Review AMD.", symbols=("AMD",), as_of=as_of)

    result = NewsContextProvider(service).build_context(request)

    assert service.queries == [
        NewsQuery(
            symbols=["AMD"],
            published_after=as_of - timedelta(days=7),
            published_before=as_of,
        )
    ]
    assert result.provider_name == "news"
    assert result.metadata == {"source": "news_service"}
    assert result.partial_context.news is not None
    assert result.partial_context.news.source == "news"
    assert result.partial_context.news.fetched_at == as_of
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

    assert service.queries == [
        NewsQuery(
            symbols=["POET"],
            published_after=as_of - timedelta(days=7),
            published_before=as_of,
        )
    ]
    assert result.partial_context.news is not None
    assert result.partial_context.news.items == ()
    assert result.partial_context.news.fetched_at == as_of


def test_news_context_provider_allocates_news_limit_per_symbol() -> None:
    as_of = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    articles = [
        NewsArticle(
            title=f"{symbol} news {index}",
            url=f"https://example.com/{symbol.lower()}/{index}",
            source="Test Wire",
            published_at=as_of - timedelta(hours=index + 1),
            symbols=[symbol],
        )
        for symbol in ("AMD", "NVDA")
        for index in range(4)
    ]
    service = RecordingNewsService(articles)
    request = ContextRequest(
        question="Review AMD and NVDA.",
        symbols=("AMD", "NVDA"),
        as_of=as_of,
    )

    result = NewsContextProvider(service, per_symbol_limit=2).build_context(request)

    assert [query.symbols for query in service.queries] == [["AMD"], ["NVDA"]]
    assert result.partial_context.news is not None
    counts = Counter(item.symbol for item in result.partial_context.news.items)
    assert counts == {"AMD": 2, "NVDA": 2}


def test_news_context_provider_falls_back_from_three_to_seven_days() -> None:
    as_of = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    older_article = NewsArticle(
        title="Older but still relevant filing coverage",
        url="https://example.com/amd/older",
        source="Test Wire",
        published_at=as_of - timedelta(days=5),
        symbols=["AMD"],
    )
    service = RecordingNewsService([older_article])
    request = ContextRequest("Review AMD.", ("AMD",), as_of=as_of)

    result = NewsContextProvider(service).build_context(request)

    assert result.partial_context.news is not None
    assert [item.title for item in result.partial_context.news.items] == [
        older_article.title
    ]


def test_news_context_provider_rejects_requests_without_symbols() -> None:
    service = RecordingNewsService([])
    provider = NewsContextProvider(service)
    request = ContextRequest(question="Review the market.", symbols=())

    with pytest.raises(UnsupportedContextRequestError):
        provider.build_context(request)

    assert service.queries == []
