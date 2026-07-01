"""Deterministic market sentiment scoring and classification."""

from __future__ import annotations

from parakeetnest.intelligence.sentiment.models import (
    MarketSentimentSnapshot,
    SentimentRegime,
    SentimentSignal,
)


class MarketSentimentCalculator:
    """Calculate market sentiment snapshots from provider-neutral inputs."""

    def calculate(
        self,
        snapshot: MarketSentimentSnapshot,
    ) -> MarketSentimentSnapshot:
        """Return a deterministic snapshot with score, regime, and confidence."""
        signals = self.normalize_signals(snapshot.signals)
        overall_score = self.calculate_score(signals)
        regime = self.classify_sentiment(overall_score)

        return MarketSentimentSnapshot(
            as_of=snapshot.as_of,
            overall_score=overall_score,
            confidence=self.confidence_for(signals, overall_score),
            regime=regime,
            signals=signals,
            summary=self.summary_for(regime, overall_score),
        )

    def normalize_signals(
        self,
        signals: tuple[SentimentSignal, ...],
    ) -> tuple[SentimentSignal, ...]:
        """Return normalized 0-100 sentiment signals from raw indicators."""
        return tuple(self._normalize_signal(signal) for signal in signals)

    @staticmethod
    def calculate_score(signals: tuple[SentimentSignal, ...]) -> float:
        """Return a weighted sentiment score between 0.0 and 100.0."""
        total_weight = sum(max(signal.weight, 0.0) for signal in signals)
        if total_weight <= 0:
            return 50.0

        weighted_score = sum(
            MarketSentimentCalculator._clamp_score(signal.normalized_score)
            * max(signal.weight, 0.0)
            for signal in signals
        )
        return round(
            MarketSentimentCalculator._clamp_score(weighted_score / total_weight),
            4,
        )

    @staticmethod
    def classify_sentiment(score: float) -> SentimentRegime:
        """Return the sentiment regime for a 0-100 score."""
        normalized_score = MarketSentimentCalculator._clamp_score(score)
        if normalized_score >= 80:
            return SentimentRegime.EXTREME_GREED
        if normalized_score >= 60:
            return SentimentRegime.GREED
        if normalized_score >= 40:
            return SentimentRegime.NEUTRAL
        if normalized_score >= 20:
            return SentimentRegime.FEAR
        return SentimentRegime.EXTREME_FEAR

    @classmethod
    def confidence_for(
        cls,
        signals: tuple[SentimentSignal, ...],
        overall_score: float,
    ) -> float:
        """Return confidence based on signal coverage and agreement."""
        if not signals:
            return 0.0

        scores = tuple(cls._clamp_score(signal.normalized_score) for signal in signals)
        bullish_signals = sum(score >= 50 for score in scores)
        agreement = bullish_signals / len(scores)
        if agreement < 0.50:
            agreement = 1.0 - agreement

        coverage = sum(max(signal.weight, 0.0) for signal in signals)
        conviction = abs(cls._clamp_score(overall_score) - 50) / 50
        confidence = 0.40 + (0.30 * min(coverage, 1.0)) + (0.20 * agreement)
        confidence += 0.10 * conviction
        return round(cls._clamp_unit(confidence), 4)

    @staticmethod
    def summary_for(regime: SentimentRegime, overall_score: float) -> str:
        """Return a short deterministic summary for the sentiment snapshot."""
        return (
            f"Market sentiment classified as {regime.value} "
            f"with a {round(overall_score, 2)} score."
        )

    @classmethod
    def _normalize_signal(cls, signal: SentimentSignal) -> SentimentSignal:
        name = signal.name.strip().lower()
        if name == "vix level":
            normalized_score = cls._normalize_inverse(signal.value, low=12, high=40)
        elif name == "vix trend":
            normalized_score = cls._normalize_inverse(
                signal.value,
                low=-0.20,
                high=0.40,
            )
        elif name == "put/call proxy":
            normalized_score = cls._normalize_inverse(
                signal.value,
                low=0.70,
                high=1.30,
            )
        elif name == "credit stress":
            normalized_score = cls._normalize_inverse(signal.value, low=1.0, high=6.0)
        elif name == "safe-haven demand":
            normalized_score = cls._normalize_inverse(
                signal.value,
                low=-0.05,
                high=0.10,
            )
        elif name == "risk appetite":
            normalized_score = cls._normalize_direct(
                signal.value,
                low=-0.10,
                high=0.15,
            )
        else:
            normalized_score = cls._clamp_score(signal.normalized_score)

        return SentimentSignal(
            name=signal.name,
            value=signal.value,
            normalized_score=normalized_score,
            weight=signal.weight,
            description=signal.description,
        )

    @staticmethod
    def _normalize_direct(value: float, *, low: float, high: float) -> float:
        return MarketSentimentCalculator._clamp_score(
            ((float(value) - low) / (high - low)) * 100
        )

    @staticmethod
    def _normalize_inverse(value: float, *, low: float, high: float) -> float:
        return 100 - MarketSentimentCalculator._normalize_direct(
            value,
            low=low,
            high=high,
        )

    @staticmethod
    def _clamp_score(value: float) -> float:
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def _clamp_unit(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


__all__ = ["MarketSentimentCalculator"]
