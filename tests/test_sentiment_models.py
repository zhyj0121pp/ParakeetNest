"""Tests for Market Sentiment Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date

import pytest

from parakeetnest.intelligence.sentiment import (
    MarketSentimentSnapshot,
    SentimentRegime,
    SentimentSignal,
)


AS_OF_DATE = date(2026, 6, 30)


def test_sentiment_regime_values_are_stable() -> None:
    """Fear/greed enum values should remain stable for downstream consumers."""
    assert [regime.value for regime in SentimentRegime] == [
        "extreme_fear",
        "fear",
        "neutral",
        "greed",
        "extreme_greed",
    ]


def test_sentiment_signal_fields_are_provider_neutral() -> None:
    """Signals should contain structured indicator facts and weights only."""
    field_names = {field.name for field in fields(SentimentSignal)}

    assert field_names == {
        "name",
        "value",
        "normalized_score",
        "weight",
        "description",
    }


def test_sentiment_signal_normalizes_values_and_is_immutable() -> None:
    """Signal values should normalize types without provider-specific payloads."""
    signal = SentimentSignal(
        name=" VIX level ",
        value="18.5",
        normalized_score="65",
        weight="0.20",
        description=" structured signal ",
    )

    assert signal.name == "VIX level"
    assert signal.value == 18.5
    assert signal.normalized_score == 65.0
    assert signal.weight == 0.20
    assert signal.description == "structured signal"

    with pytest.raises(FrozenInstanceError):
        signal.weight = 0.1


def test_market_sentiment_snapshot_fields_are_provider_neutral() -> None:
    """Snapshots should not contain recommendation, vendor, or LLM fields."""
    field_names = {field.name for field in fields(MarketSentimentSnapshot)}

    assert field_names == {
        "as_of",
        "overall_score",
        "confidence",
        "regime",
        "signals",
        "summary",
    }


def test_market_sentiment_snapshot_normalizes_values_and_is_immutable() -> None:
    """Snapshots should normalize score, confidence, enum, signals, and summary."""
    signal = SentimentSignal(
        name="Risk appetite",
        value=0.07,
        normalized_score=68,
        weight=0.15,
    )
    snapshot = MarketSentimentSnapshot(
        as_of=AS_OF_DATE,
        overall_score="65.5",
        confidence="0.82",
        regime="greed",
        signals=[signal],
        summary=" constructive sentiment ",
    )

    assert snapshot.overall_score == 65.5
    assert snapshot.confidence == 0.82
    assert snapshot.regime is SentimentRegime.GREED
    assert snapshot.signals == (signal,)
    assert snapshot.summary == "constructive sentiment"

    with pytest.raises(FrozenInstanceError):
        snapshot.confidence = 0.1
