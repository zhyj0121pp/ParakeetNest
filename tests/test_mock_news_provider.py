"""Tests for the deterministic mock news provider."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.news import MockNewsProvider, NewsArticle, NewsProvider, NewsQuery


def test_mock_provider_returns_deterministic_articles() -> None:
    """Repeated calls and provider instances should return identical articles."""
    first_provider = MockNewsProvider()
    second_provider = MockNewsProvider()

    first_articles = first_provider.get_news(NewsQuery())
    second_articles = second_provider.get_news(NewsQuery())

    assert first_articles == second_articles
    assert len(first_articles) == 5
    assert all(isinstance(article, NewsArticle) for article in first_articles)
    assert first_articles[0].title == "AMD expands AI accelerator roadmap"
    assert first_articles[0].published_at == datetime(
        2026,
        6,
        29,
        12,
        0,
        tzinfo=UTC,
    )


def test_mock_provider_applies_limit() -> None:
    """The mock provider should honor the provider-neutral query limit."""
    provider = MockNewsProvider()

    articles = provider.get_news(NewsQuery(limit=2))

    assert [article.title for article in articles] == [
        "AMD expands AI accelerator roadmap",
        "Apple services growth offsets hardware caution",
    ]


def test_mock_provider_filters_by_symbol() -> None:
    """Symbol filtering should match any tagged article symbol."""
    provider = MockNewsProvider()

    articles = provider.get_news(NewsQuery(symbols=["msft"]))

    assert len(articles) == 1
    assert articles[0].title == "Nvidia and Microsoft deepen cloud AI collaboration"
    assert articles[0].symbols == ["NVDA", "MSFT"]


def test_mock_provider_filters_by_keywords() -> None:
    """Keyword filtering should search titles, summaries, and sources."""
    provider = MockNewsProvider()

    articles = provider.get_news(NewsQuery(keywords=["cloud", "collaboration"]))

    assert len(articles) == 1
    assert articles[0].title == "Nvidia and Microsoft deepen cloud AI collaboration"


def test_mock_provider_combines_symbol_and_keyword_filters() -> None:
    """Symbol and keyword filters should narrow results together."""
    provider = MockNewsProvider()

    articles = provider.get_news(NewsQuery(symbols=["SPY"], keywords=["Fed"]))

    assert len(articles) == 1
    assert articles[0].title == "Broad market ETF inflows continue after Fed commentary"


def test_mock_provider_returns_fresh_lists() -> None:
    """Mutating returned lists should not affect later calls."""
    provider = MockNewsProvider()

    articles = provider.get_news(NewsQuery())
    articles.clear()

    assert len(provider.get_news(NewsQuery())) == 5


def test_mock_provider_satisfies_news_provider_protocol() -> None:
    """The mock provider should be usable through the provider protocol."""
    provider: NewsProvider = MockNewsProvider()

    assert isinstance(provider, NewsProvider)
    assert provider.get_news(NewsQuery(symbols=["AMD"]))[0].source == "Parakeet Wire"
