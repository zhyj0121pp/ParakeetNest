"""Deterministic mock provider for Market Sentiment Layer intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.sentiment.models import (
    MarketSentimentSnapshot,
    SentimentRegime,
    SentimentSignal,
)


class MockMarketSentimentProvider:
    """Return injected or default sentiment snapshots without external I/O."""

    def __init__(self, snapshot: MarketSentimentSnapshot | None = None) -> None:
        """Initialize the provider with an optional fixed snapshot fixture."""
        self._snapshot = snapshot
        self.calls: list[date | None] = []

    def get_sentiment_snapshot(
        self,
        *,
        as_of: date | None = None,
    ) -> MarketSentimentSnapshot:
        """Return injected inputs or deterministic sample sentiment facts."""
        self.calls.append(as_of)

        if self._snapshot is not None:
            return self._snapshot

        observed_on = as_of or date(2026, 6, 30)
        return MarketSentimentSnapshot(
            as_of=observed_on,
            overall_score=0,
            confidence=0,
            regime=SentimentRegime.NEUTRAL,
            signals=(
                SentimentSignal(
                    name="VIX level",
                    value=18.6,
                    normalized_score=0,
                    weight=0.22,
                    description="Lower volatility implies stronger sentiment.",
                ),
                SentimentSignal(
                    name="VIX trend",
                    value=-0.08,
                    normalized_score=0,
                    weight=0.16,
                    description="Falling volatility supports risk appetite.",
                ),
                SentimentSignal(
                    name="Put/Call proxy",
                    value=0.88,
                    normalized_score=0,
                    weight=0.17,
                    description="Lower put/call pressure implies stronger sentiment.",
                ),
                SentimentSignal(
                    name="Credit stress",
                    value=2.35,
                    normalized_score=0,
                    weight=0.16,
                    description="Lower credit stress implies stronger sentiment.",
                ),
                SentimentSignal(
                    name="Safe-haven demand",
                    value=0.01,
                    normalized_score=0,
                    weight=0.14,
                    description="Lower safe-haven demand implies stronger sentiment.",
                ),
                SentimentSignal(
                    name="Risk appetite",
                    value=0.07,
                    normalized_score=0,
                    weight=0.15,
                    description="Higher risk appetite implies stronger sentiment.",
                ),
            ),
            summary=None,
        )


__all__ = ["MockMarketSentimentProvider"]
