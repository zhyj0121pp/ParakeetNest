"""Provider-neutral Market Sentiment Layer public API.

The package exports the deterministic Market Sentiment Layer surface: domain
models, provider protocol, calculator, orchestration service, and network-free
mock provider.
"""

from parakeetnest.intelligence.sentiment.calculator import MarketSentimentCalculator
from parakeetnest.intelligence.sentiment.mock import MockMarketSentimentProvider
from parakeetnest.intelligence.sentiment.models import (
    MarketSentimentSnapshot,
    SentimentRegime,
    SentimentSignal,
)
from parakeetnest.intelligence.sentiment.provider import (
    MarketSentimentProvider,
)
from parakeetnest.intelligence.sentiment.service import MarketSentimentService

__all__ = [
    "MarketSentimentCalculator",
    "MarketSentimentProvider",
    "MarketSentimentService",
    "MarketSentimentSnapshot",
    "MockMarketSentimentProvider",
    "SentimentRegime",
    "SentimentSignal",
]
