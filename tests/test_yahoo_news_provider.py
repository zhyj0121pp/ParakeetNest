"""Tests for the Yahoo Finance news provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.config import AppConfig
from parakeetnest.app import create_app
from parakeetnest.market_data import (
    MalformedMarketDataError,
    ProviderUnavailableError,
)
from parakeetnest.news import (
    NewsArticle,
    NewsProvider,
    NewsQuery,
    YahooFinanceNewsProvider,
)


class FakeTicker:
    """Minimal yfinance Ticker double used to avoid network calls."""

    def __init__(self, symbol: str, news: object | None = None) -> None:
        self.symbol = symbol
        self.news = (
            [
                {
                    "content": {
                        "title": "AMD expands AI accelerator roadmap",
                        "canonicalUrl": {
                            "url": "https://finance.yahoo.com/news/amd-ai-roadmap"
                        },
                        "provider": {"displayName": "Reuters"},
                        "pubDate": "2026-06-29T13:00:00Z",
                        "summary": "AMD outlined new data center accelerator milestones.",
                        "finance": {
                            "stockTickers": [
                                {"symbol": "AMD"},
                                {"symbol": "NVDA"},
                            ]
                        },
                    }
                }
            ]
            if news is None
            else news
        )
        self.news_calls: list[tuple[int, str]] = []

    def get_news(self, *, count: int, tab: str) -> object:
        self.news_calls.append((count, tab))
        return self.news


class FakeYFinance:
    """Minimal yfinance module double."""

    def __init__(self, news: object | None = None) -> None:
        self.news = news
        self.tickers: list[FakeTicker] = []

    def Ticker(self, symbol: str) -> FakeTicker:
        ticker = FakeTicker(symbol, self.news)
        self.tickers.append(ticker)
        return ticker


def test_yahoo_news_provider_satisfies_news_provider_protocol() -> None:
    provider: NewsProvider = YahooFinanceNewsProvider(FakeYFinance())

    assert isinstance(provider, NewsProvider)


def test_get_news_maps_yahoo_content_payload_to_news_article() -> None:
    provider = YahooFinanceNewsProvider(FakeYFinance())

    articles = provider.get_news(NewsQuery(symbols=["amd"]))

    assert articles == [
        NewsArticle(
            title="AMD expands AI accelerator roadmap",
            url="https://finance.yahoo.com/news/amd-ai-roadmap",
            source="Reuters",
            published_at=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            summary="AMD outlined new data center accelerator milestones.",
            symbols=["AMD", "NVDA"],
            provider="yahoo",
        )
    ]
    assert provider._yf.tickers[0].news_calls == [(10, "news")]


def test_get_news_filters_by_publication_window() -> None:
    provider = YahooFinanceNewsProvider(FakeYFinance())

    articles = provider.get_news(
        NewsQuery(
            symbols=["AMD"],
            published_after=datetime(2026, 6, 30, tzinfo=UTC),
        )
    )

    assert articles == []


def test_get_news_maps_flat_yahoo_payload_to_news_article() -> None:
    fake_yfinance = FakeYFinance(
        news=[
            {
                "title": "Apple services growth offsets hardware caution",
                "link": "https://finance.yahoo.com/news/apple-services-growth",
                "publisher": "Yahoo Finance",
                "providerPublishTime": 1_782_738_000,
                "summary": "Analysts highlighted services revenue resilience.",
                "relatedTickers": ["AAPL"],
            }
        ]
    )
    provider = YahooFinanceNewsProvider(fake_yfinance)

    articles = provider.get_news(NewsQuery(symbols=["aapl"]))

    assert articles == [
        NewsArticle(
            title="Apple services growth offsets hardware caution",
            url="https://finance.yahoo.com/news/apple-services-growth",
            source="Yahoo Finance",
            published_at=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            summary="Analysts highlighted services revenue resilience.",
            symbols=["AAPL"],
            provider="yahoo",
        )
    ]


def test_get_news_returns_empty_list_for_empty_response() -> None:
    provider = YahooFinanceNewsProvider(
        FakeYFinance(news=[]),
        retry_delay_seconds=0,
    )

    articles = provider.get_news(NewsQuery(symbols=["amd"]))

    assert articles == []


def test_get_news_raises_malformed_error_for_non_list_response() -> None:
    provider = YahooFinanceNewsProvider(
        FakeYFinance(news={"title": "bad shape"}),
        retry_delay_seconds=0,
    )

    with pytest.raises(MalformedMarketDataError, match="non-list news payload"):
        provider.get_news(NewsQuery(symbols=["amd"]))


def test_get_news_raises_malformed_error_for_missing_required_fields() -> None:
    provider = YahooFinanceNewsProvider(
        FakeYFinance(news=[{"title": "Missing URL"}]),
        retry_delay_seconds=0,
    )

    with pytest.raises(MalformedMarketDataError, match="without url"):
        provider.get_news(NewsQuery(symbols=["amd"]))


def test_timeout_maps_to_provider_unavailable() -> None:
    class TimeoutYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> FakeTicker:
            raise TimeoutError("read timed out")

    provider = YahooFinanceNewsProvider(
        TimeoutYFinance(),
        max_attempts=1,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError, match="temporarily unavailable"):
        provider.get_news(NewsQuery(symbols=["amd"]))


def test_retry_succeeds_after_transient_failure() -> None:
    class FlakyYFinance(FakeYFinance):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def Ticker(self, symbol: str) -> FakeTicker:
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("read timed out")
            return super().Ticker(symbol)

    fake_yfinance = FlakyYFinance()
    provider = YahooFinanceNewsProvider(
        fake_yfinance,
        max_attempts=2,
        retry_delay_seconds=0,
    )

    articles = provider.get_news(NewsQuery(symbols=["amd"]))

    assert articles[0].title == "AMD expands AI accelerator roadmap"
    assert fake_yfinance.calls == 2


def test_retry_exhausted_raises_provider_unavailable() -> None:
    class AlwaysTimeoutYFinance(FakeYFinance):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def Ticker(self, symbol: str) -> FakeTicker:
            self.calls += 1
            raise TimeoutError("read timed out")

    fake_yfinance = AlwaysTimeoutYFinance()
    provider = YahooFinanceNewsProvider(
        fake_yfinance,
        max_attempts=3,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError):
        provider.get_news(NewsQuery(symbols=["amd"]))

    assert fake_yfinance.calls == 3


def test_provider_exception_does_not_escape() -> None:
    class YahooBoom(Exception):
        pass

    class BrokenYFinance(FakeYFinance):
        def Ticker(self, symbol: str) -> FakeTicker:
            raise YahooBoom("provider exploded")

    provider = YahooFinanceNewsProvider(
        BrokenYFinance(),
        max_attempts=1,
        retry_delay_seconds=0,
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider.get_news(NewsQuery(symbols=["amd"]))

    assert not isinstance(exc_info.value, YahooBoom)


def test_configuration_selection_uses_yahoo_provider(tmp_path) -> None:
    app = create_app(
        AppConfig(
            database_url=f"sqlite:///{tmp_path / 'parakeetnest.sqlite3'}",
            llm_provider="mock",
            news={"provider": "yahoo"},
            environment="test",
        )
    )

    try:
        assert isinstance(app.news_service._provider, YahooFinanceNewsProvider)
    finally:
        app.close()
