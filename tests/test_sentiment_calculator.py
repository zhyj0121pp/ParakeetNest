"""Tests for deterministic market sentiment calculations."""

from __future__ import annotations

import inspect
import sys
from datetime import date

import pytest

from parakeetnest.intelligence.sentiment import (
    MarketSentimentCalculator,
    MarketSentimentSnapshot,
    SentimentRegime,
    SentimentSignal,
)


AS_OF_DATE = date(2026, 6, 30)


def raw_snapshot(
    *,
    vix_level: float = 18.6,
    vix_trend: float = -0.08,
    put_call_proxy: float = 0.88,
    credit_stress: float = 2.35,
    safe_haven_demand: float = 0.01,
    risk_appetite: float = 0.07,
) -> MarketSentimentSnapshot:
    """Build one raw provider-neutral sentiment snapshot."""
    return MarketSentimentSnapshot(
        as_of=AS_OF_DATE,
        overall_score=0,
        confidence=0,
        regime=SentimentRegime.NEUTRAL,
        signals=(
            SentimentSignal("VIX level", vix_level, 0, 0.22),
            SentimentSignal("VIX trend", vix_trend, 0, 0.16),
            SentimentSignal("Put/Call proxy", put_call_proxy, 0, 0.17),
            SentimentSignal("Credit stress", credit_stress, 0, 0.16),
            SentimentSignal("Safe-haven demand", safe_haven_demand, 0, 0.14),
            SentimentSignal("Risk appetite", risk_appetite, 0, 0.15),
        ),
    )


def test_calculator_returns_greed_snapshot_for_constructive_inputs() -> None:
    """Constructive market inputs should classify as greed."""
    snapshot = MarketSentimentCalculator().calculate(raw_snapshot())

    assert isinstance(snapshot, MarketSentimentSnapshot)
    assert 60 <= snapshot.overall_score < 80
    assert snapshot.regime is SentimentRegime.GREED
    assert 0.0 <= snapshot.confidence <= 1.0


def test_calculator_returns_extreme_fear_snapshot() -> None:
    """Deeply stressed inputs should classify as extreme fear."""
    snapshot = MarketSentimentCalculator().calculate(
        raw_snapshot(
            vix_level=44,
            vix_trend=0.42,
            put_call_proxy=1.40,
            credit_stress=6.5,
            safe_haven_demand=0.12,
            risk_appetite=-0.12,
        )
    )

    assert snapshot.overall_score < 20
    assert snapshot.regime is SentimentRegime.EXTREME_FEAR


def test_calculator_returns_neutral_snapshot() -> None:
    """Midpoint inputs should classify as neutral."""
    snapshot = MarketSentimentCalculator().calculate(
        raw_snapshot(
            vix_level=26,
            vix_trend=0.10,
            put_call_proxy=1.00,
            credit_stress=3.5,
            safe_haven_demand=0.025,
            risk_appetite=0.025,
        )
    )

    assert snapshot.overall_score == pytest.approx(50.0)
    assert snapshot.regime is SentimentRegime.NEUTRAL


def test_calculator_returns_extreme_greed_snapshot() -> None:
    """Very strong risk appetite inputs should classify as extreme greed."""
    snapshot = MarketSentimentCalculator().calculate(
        raw_snapshot(
            vix_level=10,
            vix_trend=-0.25,
            put_call_proxy=0.60,
            credit_stress=0.8,
            safe_haven_demand=-0.08,
            risk_appetite=0.18,
        )
    )

    assert snapshot.overall_score >= 80
    assert snapshot.regime is SentimentRegime.EXTREME_GREED


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (-10.0, SentimentRegime.EXTREME_FEAR),
        (0.0, SentimentRegime.EXTREME_FEAR),
        (19.999, SentimentRegime.EXTREME_FEAR),
        (20.0, SentimentRegime.FEAR),
        (39.999, SentimentRegime.FEAR),
        (40.0, SentimentRegime.NEUTRAL),
        (59.999, SentimentRegime.NEUTRAL),
        (60.0, SentimentRegime.GREED),
        (79.999, SentimentRegime.GREED),
        (80.0, SentimentRegime.EXTREME_GREED),
        (100.0, SentimentRegime.EXTREME_GREED),
        (150.0, SentimentRegime.EXTREME_GREED),
    ],
)
def test_classify_sentiment_uses_stable_threshold_boundaries(
    score: float,
    expected: SentimentRegime,
) -> None:
    """Sentiment thresholds should be inclusive at documented cutoffs."""
    assert MarketSentimentCalculator.classify_sentiment(score) is expected


def test_signal_normalization_clamps_extreme_provider_inputs() -> None:
    """Out-of-range raw inputs should not push signals outside the public range."""
    calculator = MarketSentimentCalculator()

    maximum = calculator.calculate(
        raw_snapshot(
            vix_level=-10,
            vix_trend=-10,
            put_call_proxy=-10,
            credit_stress=-10,
            safe_haven_demand=-10,
            risk_appetite=10,
        )
    )
    minimum = calculator.calculate(
        raw_snapshot(
            vix_level=100,
            vix_trend=10,
            put_call_proxy=10,
            credit_stress=100,
            safe_haven_demand=10,
            risk_appetite=-10,
        )
    )

    assert maximum.overall_score == 100.0
    assert minimum.overall_score == 0.0
    assert all(0.0 <= signal.normalized_score <= 100.0 for signal in maximum.signals)
    assert all(0.0 <= signal.normalized_score <= 100.0 for signal in minimum.signals)


def test_calculate_score_returns_midpoint_when_weights_are_zero() -> None:
    """Zero usable weight should produce a neutral deterministic score."""
    signals = MarketSentimentCalculator().normalize_signals(
        (
            SentimentSignal("VIX level", 18.6, 0, 0),
            SentimentSignal("VIX trend", -0.08, 0, 0),
            SentimentSignal("Put/Call proxy", 0.88, 0, 0),
            SentimentSignal("Credit stress", 2.35, 0, 0),
            SentimentSignal("Safe-haven demand", 0.01, 0, 0),
            SentimentSignal("Risk appetite", 0.07, 0, 0),
        )
    )

    assert MarketSentimentCalculator.calculate_score(signals) == 50.0


def test_confidence_is_normalized_and_higher_for_aligned_signals() -> None:
    """Confidence should stay in range and rise when signals agree."""
    calculator = MarketSentimentCalculator()

    aligned = calculator.calculate(
        raw_snapshot(
            vix_level=12,
            vix_trend=-0.20,
            put_call_proxy=0.70,
            credit_stress=1.0,
            safe_haven_demand=-0.05,
            risk_appetite=0.15,
        )
    )
    mixed = calculator.calculate(
        raw_snapshot(
            vix_level=12,
            vix_trend=0.40,
            put_call_proxy=0.70,
            credit_stress=6.0,
            safe_haven_demand=-0.05,
            risk_appetite=-0.10,
        )
    )

    assert 0.0 <= aligned.confidence <= 1.0
    assert 0.0 <= mixed.confidence <= 1.0
    assert aligned.confidence > mixed.confidence


def test_confidence_boundaries_are_clamped_and_deterministic() -> None:
    """Confidence should remain deterministic at coverage and agreement boundaries."""
    calculator = MarketSentimentCalculator()
    snapshot = calculator.calculate(raw_snapshot())

    assert 0.0 <= snapshot.confidence <= 1.0
    assert MarketSentimentCalculator.confidence_for((), 50) == 0.0


def test_normalize_signals_returns_expected_names_and_weights() -> None:
    """Signal generation should keep stable ordering for downstream rendering."""
    signals = MarketSentimentCalculator().normalize_signals(raw_snapshot().signals)

    assert tuple(signal.name for signal in signals) == (
        "VIX level",
        "VIX trend",
        "Put/Call proxy",
        "Credit stress",
        "Safe-haven demand",
        "Risk appetite",
    )
    assert sum(signal.weight for signal in signals) == pytest.approx(1.0)


def test_unknown_signal_keeps_provider_normalized_score() -> None:
    """Unknown structured indicators should remain usable when pre-normalized."""
    signals = MarketSentimentCalculator().normalize_signals(
        (SentimentSignal("Custom sentiment", 123, 75, 1),)
    )

    assert signals == (SentimentSignal("Custom sentiment", 123, 75, 1),)


def test_calculator_outputs_are_deterministic() -> None:
    """Identical inputs should produce identical snapshots."""
    calculator = MarketSentimentCalculator()
    snapshot = raw_snapshot()

    assert calculator.calculate(snapshot) == calculator.calculate(snapshot)


def test_calculator_has_no_external_dependencies() -> None:
    """The calculation layer should remain pure business logic."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "service",
        "database",
        "sqlite",
        "news",
        "social",
        "llm",
        "recommendation",
        "trading",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(
        sys.modules[MarketSentimentCalculator.__module__]
    ).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    snapshot = MarketSentimentCalculator().calculate(raw_snapshot())

    assert isinstance(snapshot, MarketSentimentSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_public_calculator_is_exported_from_sentiment_package() -> None:
    """The package should expose the deterministic calculator."""
    import parakeetnest.intelligence.sentiment as sentiment

    assert sentiment.MarketSentimentCalculator is MarketSentimentCalculator
