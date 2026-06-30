"""Deterministic market breadth calculations."""

from __future__ import annotations

from parakeetnest.intelligence.market_breadth.models import (
    BreadthRegime,
    MarketBreadthSnapshot,
)


class MarketBreadthCalculator:
    """Calculate breadth ratios, scores, and regimes from normalized snapshots."""

    def advance_decline_ratio(self, snapshot: MarketBreadthSnapshot) -> float:
        """Return the advance/decline ratio."""
        return snapshot.advancers / max(snapshot.decliners, 1)

    def new_high_low_ratio(self, snapshot: MarketBreadthSnapshot) -> float:
        """Return the new high/new low ratio."""
        return snapshot.new_highs / max(snapshot.new_lows, 1)

    def volume_ratio(self, snapshot: MarketBreadthSnapshot) -> float:
        """Return the up-volume/down-volume ratio."""
        return snapshot.up_volume / max(snapshot.down_volume, 1)

    def moving_average_participation(self, snapshot: MarketBreadthSnapshot) -> float:
        """Return average moving-average participation normalized to 0-1."""
        participation = (
            self._normalize_percent(snapshot.percent_above_20d_ma)
            + self._normalize_percent(snapshot.percent_above_50d_ma)
            + self._normalize_percent(snapshot.percent_above_200d_ma)
        ) / 3
        return self._clamp(participation)

    def calculate_score(self, snapshot: MarketBreadthSnapshot) -> float:
        """Return a normalized breadth score between 0.0 and 1.0."""
        score = (
            0.25 * self._normalize_ratio(self.advance_decline_ratio(snapshot))
            + 0.25 * self._normalize_ratio(self.new_high_low_ratio(snapshot))
            + 0.25 * self.moving_average_participation(snapshot)
            + 0.25 * self._normalize_ratio(self.volume_ratio(snapshot))
        )
        return self._clamp(score)

    @staticmethod
    def classify(score: float) -> BreadthRegime:
        """Return the breadth regime for a normalized score."""
        normalized_score = MarketBreadthCalculator._clamp(score)
        if normalized_score >= 0.80:
            return BreadthRegime.STRONG
        if normalized_score >= 0.60:
            return BreadthRegime.HEALTHY
        if normalized_score >= 0.40:
            return BreadthRegime.NEUTRAL
        if normalized_score >= 0.20:
            return BreadthRegime.WEAK
        return BreadthRegime.STRESSED

    @staticmethod
    def _normalize_ratio(ratio: float) -> float:
        if ratio <= 0:
            return 0.0
        return ratio / (ratio + 1)

    @staticmethod
    def _normalize_percent(percent: float) -> float:
        return MarketBreadthCalculator._clamp(percent / 100)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


__all__ = ["MarketBreadthCalculator"]
