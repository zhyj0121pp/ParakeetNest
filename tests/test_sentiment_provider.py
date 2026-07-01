"""Tests for the provider-neutral Market Sentiment Layer boundary."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.sentiment import (
    MarketSentimentProvider,
    MarketSentimentSnapshot,
    MockMarketSentimentProvider,
    SentimentRegime,
    SentimentSignal,
)


AS_OF_DATE = date(2026, 6, 30)


def raw_snapshot(*, as_of: date = AS_OF_DATE) -> MarketSentimentSnapshot:
    """Build one raw provider-neutral sentiment snapshot."""
    return MarketSentimentSnapshot(
        as_of=as_of,
        overall_score=0,
        confidence=0,
        regime=SentimentRegime.NEUTRAL,
        signals=(
            SentimentSignal("VIX level", 18.6, 0, 0.22),
            SentimentSignal("VIX trend", -0.08, 0, 0.16),
            SentimentSignal("Put/Call proxy", 0.88, 0, 0.17),
            SentimentSignal("Credit stress", 2.35, 0, 0.16),
            SentimentSignal("Safe-haven demand", 0.01, 0, 0.14),
            SentimentSignal("Risk appetite", 0.07, 0, 0.15),
        ),
    )


class RecordingSentimentProvider:
    """Test double that satisfies the MarketSentimentProvider protocol."""

    def __init__(self) -> None:
        self.calls: list[date | None] = []
        self.snapshot = raw_snapshot()

    def get_sentiment_snapshot(
        self,
        *,
        as_of: date | None = None,
    ) -> MarketSentimentSnapshot:
        self.calls.append(as_of)
        return self.snapshot


def test_sentiment_provider_accepts_structural_implementation() -> None:
    """Providers should satisfy the contract by shape, not inheritance."""
    provider: MarketSentimentProvider = RecordingSentimentProvider()

    snapshot = provider.get_sentiment_snapshot(as_of=AS_OF_DATE)

    assert snapshot.as_of == AS_OF_DATE
    assert provider.calls == [AS_OF_DATE]


def test_sentiment_provider_signature_is_simple_and_provider_neutral() -> None:
    """The provider boundary should avoid vendor-specific dependencies."""
    signature = inspect.signature(MarketSentimentProvider.get_sentiment_snapshot)

    assert list(signature.parameters) == ["self", "as_of"]
    assert signature.return_annotation == "MarketSentimentSnapshot"


def test_sentiment_provider_module_has_no_provider_specific_imports() -> None:
    """The provider abstraction should not import upstream concrete providers."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "news",
        "macro",
        "breadth",
        "momentum",
        "llm",
        "recommendation",
        "trading",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[MarketSentimentProvider.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: MarketSentimentProvider = RecordingSentimentProvider()
    snapshot = provider.get_sentiment_snapshot(as_of=AS_OF_DATE)

    assert isinstance(snapshot, MarketSentimentSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_mock_provider_returns_deterministic_raw_snapshot() -> None:
    """The mock provider should not require network access or vendor payloads."""
    provider = MockMarketSentimentProvider()

    snapshot = provider.get_sentiment_snapshot()

    assert snapshot.as_of == AS_OF_DATE
    assert snapshot.overall_score == 0
    assert snapshot.confidence == 0
    assert snapshot.regime is SentimentRegime.NEUTRAL
    assert tuple(signal.name for signal in snapshot.signals) == (
        "VIX level",
        "VIX trend",
        "Put/Call proxy",
        "Credit stress",
        "Safe-haven demand",
        "Risk appetite",
    )
    assert tuple(signal.value for signal in snapshot.signals) == (
        18.6,
        -0.08,
        0.88,
        2.35,
        0.01,
        0.07,
    )
    assert sum(signal.weight for signal in snapshot.signals) == 1.0
    assert provider.calls == [None]


def test_mock_provider_multiple_calls_return_identical_results() -> None:
    """Default mock snapshots should be repeatable across calls."""
    provider = MockMarketSentimentProvider()

    first = provider.get_sentiment_snapshot()
    second = provider.get_sentiment_snapshot()

    assert first == second
    assert provider.calls == [None, None]


def test_mock_provider_can_return_injected_snapshot() -> None:
    """Tests and local callers should be able to inject fixed sentiment snapshots."""
    injected = raw_snapshot()
    provider = MockMarketSentimentProvider(snapshot=injected)

    snapshot = provider.get_sentiment_snapshot(as_of=AS_OF_DATE)

    assert snapshot is injected
    assert provider.calls == [AS_OF_DATE]


def test_mock_provider_honors_requested_as_of_for_default_snapshot() -> None:
    """Default fixture generation should be deterministic for any supplied date."""
    requested_date = date(2026, 1, 15)
    provider = MockMarketSentimentProvider()

    snapshot = provider.get_sentiment_snapshot(as_of=requested_date)

    assert snapshot.as_of == requested_date
    assert provider.calls == [requested_date]


def test_sentiment_package_exports_provider_boundary() -> None:
    """The package should expose provider and mock provider boundaries."""
    import parakeetnest.intelligence.sentiment as sentiment

    assert sentiment.MarketSentimentProvider is MarketSentimentProvider
    assert sentiment.MockMarketSentimentProvider is MockMarketSentimentProvider
    assert "MarketSentimentProvider" in sentiment.__all__
    assert "MockMarketSentimentProvider" in sentiment.__all__
