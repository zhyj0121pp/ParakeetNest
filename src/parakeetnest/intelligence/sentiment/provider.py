"""Provider abstractions for Market Sentiment Layer intelligence."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from parakeetnest.intelligence.sentiment.models import MarketSentimentSnapshot


class MarketSentimentProvider(Protocol):
    """Provider-neutral contract for retrieving structured sentiment snapshots."""

    def get_sentiment_snapshot(
        self,
        *,
        as_of: date | None = None,
    ) -> MarketSentimentSnapshot:
        """Return a provider-neutral market sentiment snapshot."""


__all__ = ["MarketSentimentProvider"]
