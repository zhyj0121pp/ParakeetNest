"""Deterministic in-memory news provider."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.news.models import NewsArticle, NewsQuery


class MockNewsProvider:
    """News provider backed by embedded deterministic fixtures."""

    _ARTICLES = (
        NewsArticle(
            title="AMD expands AI accelerator roadmap",
            url="https://example.com/news/amd-ai-roadmap",
            source="Parakeet Wire",
            published_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
            summary="AMD outlined new data center accelerator milestones for AI workloads.",
            symbols=["AMD"],
            provider="mock",
        ),
        NewsArticle(
            title="Apple services growth offsets hardware caution",
            url="https://example.com/news/apple-services-growth",
            source="Parakeet Wire",
            published_at=datetime(2026, 6, 29, 11, 30, tzinfo=UTC),
            summary="Analysts highlighted services revenue resilience while watching device demand.",
            symbols=["AAPL"],
            provider="mock",
        ),
        NewsArticle(
            title="Nvidia and Microsoft deepen cloud AI collaboration",
            url="https://example.com/news/nvidia-microsoft-cloud-ai",
            source="Mock Market Desk",
            published_at=datetime(2026, 6, 29, 10, 45, tzinfo=UTC),
            summary="The companies announced expanded AI infrastructure work for cloud customers.",
            symbols=["NVDA", "MSFT"],
            provider="mock",
        ),
        NewsArticle(
            title="Broad market ETF inflows continue after Fed commentary",
            url="https://example.com/news/spy-fed-inflows",
            source="Mock Market Desk",
            published_at=datetime(2026, 6, 29, 9, 15, tzinfo=UTC),
            summary="ETF flow data showed continued demand after investors parsed Fed remarks.",
            symbols=["SPY"],
            provider="mock",
        ),
        NewsArticle(
            title="POET photonics update draws small-cap investor attention",
            url="https://example.com/news/poet-photonics-update",
            source="Parakeet Wire",
            published_at=datetime(2026, 6, 28, 16, 0, tzinfo=UTC),
            summary="The company discussed photonics milestones and customer qualification progress.",
            symbols=["POET"],
            provider="mock",
        ),
    )

    def get_news(self, query: NewsQuery) -> list[NewsArticle]:
        """Return deterministic articles matching symbols and keywords."""
        articles = list(self._ARTICLES)

        if query.symbols:
            wanted_symbols = set(query.symbols)
            articles = [
                article
                for article in articles
                if article.symbols is not None
                and wanted_symbols.intersection(article.symbols)
            ]

        if query.keywords:
            wanted_keywords = [keyword.casefold() for keyword in query.keywords]
            articles = [
                article
                for article in articles
                if self._matches_keywords(article, wanted_keywords)
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

    def _matches_keywords(
        self,
        article: NewsArticle,
        wanted_keywords: list[str],
    ) -> bool:
        searchable_text = " ".join(
            value
            for value in (
                article.title,
                article.summary,
                article.source,
            )
            if value is not None
        ).casefold()

        return all(keyword in searchable_text for keyword in wanted_keywords)


__all__ = ["MockNewsProvider"]
