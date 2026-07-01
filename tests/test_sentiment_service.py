"""Tests for the provider-neutral Market Sentiment service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.sentiment import (
    MarketSentimentCalculator,
    MarketSentimentService,
    MarketSentimentSnapshot,
    MockMarketSentimentProvider,
    SentimentRegime,
    SentimentSignal,
)


AS_OF_DATE = date(2026, 6, 30)


def sentiment_snapshot(
    *,
    as_of: date = AS_OF_DATE,
    overall_score: float = 68.0,
) -> MarketSentimentSnapshot:
    """Build one provider-neutral sentiment snapshot for service tests."""
    return MarketSentimentSnapshot(
        as_of=as_of,
        overall_score=overall_score,
        confidence=0.84,
        regime=SentimentRegime.GREED,
        signals=(
            SentimentSignal(
                name="calculator-owned signal",
                value=1,
                normalized_score=overall_score,
                weight=1,
            ),
        ),
        summary="calculator-owned summary",
    )


class RecordingProvider:
    """Provider test double that records raw snapshot requests."""

    def __init__(self, snapshot: MarketSentimentSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[date | None] = []

    def get_sentiment_snapshot(
        self,
        *,
        as_of: date | None = None,
    ) -> MarketSentimentSnapshot:
        self.calls.append(as_of)
        return self.snapshot


class RecordingCalculator:
    """Calculator test double that records service orchestration."""

    def __init__(self, snapshot: MarketSentimentSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[MarketSentimentSnapshot] = []

    def calculate(
        self,
        snapshot: MarketSentimentSnapshot,
    ) -> MarketSentimentSnapshot:
        self.calls.append(snapshot)
        return self.snapshot


def test_service_calls_provider() -> None:
    """The service should retrieve raw snapshots from the provider."""
    snapshot = sentiment_snapshot()
    provider = RecordingProvider(snapshot)
    service = MarketSentimentService(
        provider,
        RecordingCalculator(sentiment_snapshot()),
    )

    service.get_snapshot(as_of=AS_OF_DATE)

    assert provider.calls == [AS_OF_DATE]


def test_service_calls_calculator() -> None:
    """The service should pass provider snapshots to the calculator."""
    snapshot = sentiment_snapshot()
    calculator = RecordingCalculator(sentiment_snapshot())
    service = MarketSentimentService(RecordingProvider(snapshot), calculator)

    service.get_snapshot(as_of=AS_OF_DATE)

    assert calculator.calls == [snapshot]


def test_returned_snapshot_matches_calculator_output() -> None:
    """The service should return the exact calculator snapshot."""
    expected = sentiment_snapshot(overall_score=43)
    service = MarketSentimentService(
        RecordingProvider(sentiment_snapshot()),
        RecordingCalculator(expected),
    )

    result = service.get_snapshot(as_of=AS_OF_DATE)

    assert result is expected


def test_dependency_injection_works() -> None:
    """The service should accept provider and calculator duck types."""
    provider_snapshot = sentiment_snapshot(overall_score=51)
    expected = sentiment_snapshot(overall_score=62)
    provider = RecordingProvider(provider_snapshot)
    calculator = RecordingCalculator(expected)
    service = MarketSentimentService(provider, calculator)

    result = service.get_snapshot(as_of=AS_OF_DATE)

    assert provider.calls == [AS_OF_DATE]
    assert calculator.calls == [provider_snapshot]
    assert result is expected


def test_service_requires_explicit_dependencies() -> None:
    """The public constructor should keep provider and calculator injectable."""
    signature = inspect.signature(MarketSentimentService)

    assert list(signature.parameters) == ["provider", "calculator"]
    assert signature.parameters["provider"].default is inspect.Signature.empty
    assert signature.parameters["calculator"].default is inspect.Signature.empty


def test_service_preserves_optional_as_of_none() -> None:
    """The service should not invent dates before asking the provider."""
    provider = RecordingProvider(sentiment_snapshot())
    service = MarketSentimentService(
        provider,
        RecordingCalculator(sentiment_snapshot()),
    )

    service.get_snapshot()

    assert provider.calls == [None]


def test_mock_provider_works_with_real_calculator() -> None:
    """The mock provider should compose with the real calculator."""
    snapshot = sentiment_snapshot()
    provider = MockMarketSentimentProvider(snapshot=snapshot)
    service = MarketSentimentService(provider, MarketSentimentCalculator())

    result = service.get_snapshot(as_of=AS_OF_DATE)

    assert provider.calls == [AS_OF_DATE]
    assert result == MarketSentimentCalculator().calculate(snapshot)


def test_service_has_no_duplicated_business_logic() -> None:
    """The service should not score, classify, or generate summaries."""
    forbidden_names = {
        "calculate_score",
        "classify_sentiment",
        "confidence_for",
        "summary_for",
        "overall_score",
        "regime",
        "confidence",
        "signals",
        "summary",
    }
    source = inspect.getsource(sys.modules[MarketSentimentService.__module__])

    assert all(name not in source for name in forbidden_names)


def test_sentiment_package_exports_service() -> None:
    """The package should expose the public service boundary."""
    import parakeetnest.intelligence.sentiment as sentiment

    assert sentiment.MarketSentimentService is MarketSentimentService
    assert "MarketSentimentService" in sentiment.__all__


def test_sentiment_package_exports_complete_public_api() -> None:
    """The package export list should cover the Market Sentiment Layer surface."""
    import parakeetnest.intelligence.sentiment as sentiment

    assert sentiment.__all__ == [
        "MarketSentimentCalculator",
        "MarketSentimentProvider",
        "MarketSentimentService",
        "MarketSentimentSnapshot",
        "MockMarketSentimentProvider",
        "SentimentRegime",
        "SentimentSignal",
    ]
