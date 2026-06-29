"""Tests for News Layer domain models."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from parakeetnest.news import NewsArticle, NewsQuery


def test_news_article_creation_normalizes_symbols_and_is_immutable() -> None:
    """Articles should carry provider-neutral news metadata."""
    published_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    article = NewsArticle(
        title="AMD expands AI accelerator roadmap",
        url="https://example.com/news/amd-ai-roadmap",
        source="Parakeet Wire",
        published_at=published_at,
        summary="AMD outlined new data center accelerator milestones.",
        symbols=[" amd ", "NVDA"],
        provider="mock",
    )

    assert article.title == "AMD expands AI accelerator roadmap"
    assert article.url == "https://example.com/news/amd-ai-roadmap"
    assert article.source == "Parakeet Wire"
    assert article.published_at == published_at
    assert article.summary == "AMD outlined new data center accelerator milestones."
    assert article.symbols == ["AMD", "NVDA"]
    assert article.provider == "mock"

    with pytest.raises(FrozenInstanceError):
        article.title = "Changed"


def test_news_article_allows_optional_fields_to_be_absent() -> None:
    """Summary, symbols, and provider should be optional domain fields."""
    article = NewsArticle(
        title="Market update",
        url="https://example.com/news/market-update",
        source="Parakeet Wire",
        published_at=datetime(2026, 6, 29, 9, 0, tzinfo=UTC),
    )

    assert article.summary is None
    assert article.symbols is None
    assert article.provider is None


def test_news_query_defaults_and_normalization() -> None:
    """A query should default to a small provider-neutral request."""
    default_query = NewsQuery()
    filtered_query = NewsQuery(
        symbols=[" aapl ", "msft"],
        keywords=[" AI ", "cloud"],
        limit=5,
    )

    assert default_query.symbols is None
    assert default_query.keywords is None
    assert default_query.limit == 10
    assert filtered_query.symbols == ["AAPL", "MSFT"]
    assert filtered_query.keywords == ["AI", "cloud"]
    assert filtered_query.limit == 5


def test_news_query_rejects_non_positive_limit() -> None:
    """Queries should keep provider requests bounded to positive result counts."""
    with pytest.raises(ValueError, match="limit must be at least 1"):
        NewsQuery(limit=0)
