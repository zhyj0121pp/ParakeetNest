"""Deterministic momentum calculations."""

from __future__ import annotations

from parakeetnest.intelligence.momentum.models import (
    MomentumRegime,
    MomentumSnapshot,
    ReversalRisk,
)
from parakeetnest.intelligence.momentum.provider import MomentumInputs


class MomentumCalculator:
    """Calculate momentum snapshots from normalized momentum inputs."""

    def calculate(self, inputs: MomentumInputs) -> MomentumSnapshot:
        """Return a deterministic momentum snapshot."""
        momentum_score = self.calculate_score(inputs)
        momentum_regime = self.classify_momentum(momentum_score)
        reversal_risk = self.classify_reversal_risk(inputs)

        return MomentumSnapshot(
            symbol=inputs.symbol,
            as_of=inputs.as_of,
            price_change_1m=inputs.price_change_1m,
            price_change_3m=inputs.price_change_3m,
            price_change_6m=inputs.price_change_6m,
            relative_strength=inputs.relative_strength,
            trend_strength=inputs.trend_strength,
            momentum_score=momentum_score,
            momentum_regime=momentum_regime,
            reversal_risk=reversal_risk,
            confidence=self.confidence_for(inputs, momentum_score),
            evidence=self.evidence_for(inputs, momentum_regime, reversal_risk),
        )

    def calculate_score(self, inputs: MomentumInputs) -> float:
        """Return a normalized momentum score between 0.0 and 1.0."""
        score = (
            0.15 * self._normalize_return(inputs.price_change_1m)
            + 0.25 * self._normalize_return(inputs.price_change_3m)
            + 0.30 * self._normalize_return(inputs.price_change_6m)
            + 0.15 * self._normalize_relative_strength(inputs.relative_strength)
            + 0.15 * self._normalize_trend_strength(inputs.trend_strength)
        )
        return self._clamp(score)

    @staticmethod
    def classify_momentum(score: float) -> MomentumRegime:
        """Return the momentum regime for a normalized score."""
        normalized_score = MomentumCalculator._clamp(score)
        if normalized_score >= 0.75:
            return MomentumRegime.STRONG_UPTREND
        if normalized_score >= 0.58:
            return MomentumRegime.UPTREND
        if normalized_score >= 0.42:
            return MomentumRegime.NEUTRAL
        if normalized_score >= 0.25:
            return MomentumRegime.DOWNTREND
        return MomentumRegime.STRONG_DOWNTREND

    @classmethod
    def classify_reversal_risk(cls, inputs: MomentumInputs) -> ReversalRisk:
        """Classify reversal risk from short, medium, and long-term trends."""
        short_term_extension = inputs.price_change_1m - (inputs.price_change_3m / 3)
        medium_term_trend = inputs.price_change_3m
        long_term_trend = inputs.price_change_6m

        if (
            short_term_extension >= 0.08
            and medium_term_trend > 0.08
            and long_term_trend > 0.15
        ) or (
            inputs.price_change_1m >= 0.15
            and medium_term_trend > 0
            and long_term_trend > 0
        ):
            return ReversalRisk.HIGH

        if (
            short_term_extension <= 0.03
            and medium_term_trend >= 0.03
            and long_term_trend >= 0.08
        ) or (
            abs(inputs.price_change_1m) <= 0.04
            and abs(medium_term_trend) <= 0.08
            and abs(long_term_trend) <= 0.12
        ):
            return ReversalRisk.LOW

        return ReversalRisk.MEDIUM

    @classmethod
    def confidence_for(cls, inputs: MomentumInputs, momentum_score: float) -> float:
        """Return confidence based on signal agreement and score conviction."""
        normalized_components = (
            cls._normalize_return(inputs.price_change_1m),
            cls._normalize_return(inputs.price_change_3m),
            cls._normalize_return(inputs.price_change_6m),
            cls._normalize_relative_strength(inputs.relative_strength),
            cls._normalize_trend_strength(inputs.trend_strength),
        )
        positive_signals = sum(component >= 0.50 for component in normalized_components)
        agreement = positive_signals / len(normalized_components)
        if agreement < 0.50:
            agreement = 1.0 - agreement

        conviction = abs(cls._clamp(momentum_score) - 0.50) * 2
        confidence = 0.45 + (0.35 * agreement) + (0.20 * conviction)
        return round(cls._clamp(confidence), 4)

    @classmethod
    def evidence_for(
        cls,
        inputs: MomentumInputs,
        momentum_regime: MomentumRegime,
        reversal_risk: ReversalRisk,
    ) -> tuple[str, ...]:
        """Return human-readable evidence for the calculated snapshot."""
        evidence = [
            cls._six_month_evidence(inputs.price_change_6m),
            cls._relative_strength_evidence(inputs.relative_strength),
            cls._short_term_evidence(inputs),
            cls._trend_strength_evidence(inputs.trend_strength),
            f"Momentum regime classified as {momentum_regime.value}.",
            f"Reversal risk classified as {reversal_risk.value}.",
        ]
        return tuple(evidence)

    @staticmethod
    def _six_month_evidence(price_change_6m: float) -> str:
        if price_change_6m >= 0.20:
            return "Strong 6-month trend."
        if price_change_6m >= 0.08:
            return "Positive 6-month trend."
        if price_change_6m <= -0.20:
            return "Strong negative 6-month trend."
        if price_change_6m <= -0.08:
            return "Negative 6-month trend."
        return "6-month trend is neutral."

    @staticmethod
    def _relative_strength_evidence(relative_strength: float) -> str:
        if relative_strength >= 70:
            return "Relative strength above market."
        if relative_strength <= 30:
            return "Relative strength below market."
        return "Relative strength near market."

    @staticmethod
    def _short_term_evidence(inputs: MomentumInputs) -> str:
        expected_one_month = inputs.price_change_3m / 3
        if inputs.price_change_1m > expected_one_month + 0.02:
            return "Short-term momentum accelerating."
        if inputs.price_change_1m < expected_one_month - 0.02:
            return "Short-term momentum decelerating."
        return "Short-term momentum aligned with medium-term trend."

    @staticmethod
    def _trend_strength_evidence(trend_strength: float) -> str:
        if trend_strength >= 0.70:
            return "Trend strength is strong."
        if trend_strength <= 0.30:
            return "Trend strength is weak."
        return "Trend strength is moderate."

    @staticmethod
    def _normalize_return(period_return: float) -> float:
        return MomentumCalculator._clamp((float(period_return) + 0.30) / 0.60)

    @staticmethod
    def _normalize_relative_strength(relative_strength: float) -> float:
        return MomentumCalculator._clamp(float(relative_strength) / 100)

    @staticmethod
    def _normalize_trend_strength(trend_strength: float) -> float:
        return MomentumCalculator._clamp(trend_strength)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


__all__ = ["MomentumCalculator"]
