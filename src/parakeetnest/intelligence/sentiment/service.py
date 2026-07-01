"""Service boundary for provider-neutral Market Sentiment Layer intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.sentiment.calculator import MarketSentimentCalculator
from parakeetnest.intelligence.sentiment.models import MarketSentimentSnapshot
from parakeetnest.intelligence.sentiment.provider import MarketSentimentProvider


class MarketSentimentService:
    """Public application boundary for market sentiment snapshots."""

    def __init__(
        self,
        provider: MarketSentimentProvider,
        calculator: MarketSentimentCalculator,
    ) -> None:
        """Initialize the service with explicit provider and calculator dependencies."""
        self._provider = provider
        self._calculator = calculator

    def get_snapshot(
        self,
        *,
        as_of: date | None = None,
    ) -> MarketSentimentSnapshot:
        """Return a provider-neutral market sentiment snapshot."""
        snapshot = self._provider.get_sentiment_snapshot(as_of=as_of)
        return self._calculator.calculate(snapshot)


__all__ = ["MarketSentimentService"]
