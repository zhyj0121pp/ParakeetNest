"""Deterministic risk calculations."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.risk.models import (
    RiskAssessment,
    RiskLevel,
    RiskSignal,
)


class RiskCalculator:
    """Calculate aggregate risk assessments from normalized risk signals."""

    def calculate(
        self,
        signals: list[RiskSignal],
        *,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        """Return a deterministic aggregate assessment from risk signals."""
        has_extreme_signal = any(signal.level is RiskLevel.EXTREME for signal in signals)
        normalized_signals = [self._normalize_signal(signal) for signal in signals]
        if not normalized_signals:
            return RiskAssessment(
                overall_level=RiskLevel.LOW,
                overall_score=0.0,
                signals=[],
                as_of_date=as_of_date,
                summary="No risk signals available.",
                source="risk_calculator",
            )

        overall_score = sum(signal.score for signal in normalized_signals) / len(
            normalized_signals
        )
        overall_level = self._level_for_score(overall_score)

        if has_extreme_signal or any(
            signal.level is RiskLevel.EXTREME for signal in normalized_signals
        ):
            overall_level = self._max_level(overall_level, RiskLevel.HIGH)

        return RiskAssessment(
            overall_level=overall_level,
            overall_score=overall_score,
            signals=normalized_signals,
            as_of_date=as_of_date,
            summary=self._build_summary(normalized_signals, overall_level),
            source="risk_calculator",
        )

    @classmethod
    def _normalize_signal(cls, signal: RiskSignal) -> RiskSignal:
        score = cls._clamp_score(signal.score)
        return RiskSignal(
            category=signal.category,
            level=cls._level_for_score(score),
            score=score,
            label=signal.label,
            description=signal.description,
            evidence=signal.evidence,
            metadata=signal.metadata,
        )

    @staticmethod
    def _clamp_score(score: float) -> float:
        return max(0.0, min(1.0, float(score)))

    @staticmethod
    def _level_for_score(score: float) -> RiskLevel:
        if score <= 0.20:
            return RiskLevel.LOW
        if score <= 0.40:
            return RiskLevel.MODERATE
        if score <= 0.60:
            return RiskLevel.ELEVATED
        if score <= 0.80:
            return RiskLevel.HIGH
        return RiskLevel.EXTREME

    @staticmethod
    def _max_level(first: RiskLevel, other: RiskLevel) -> RiskLevel:
        ordering = {
            RiskLevel.LOW: 0,
            RiskLevel.MODERATE: 1,
            RiskLevel.ELEVATED: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.EXTREME: 4,
        }
        return first if ordering[first] >= ordering[other] else other

    @staticmethod
    def _build_summary(signals: list[RiskSignal], overall_level: RiskLevel) -> str:
        return (
            "Calculated risk assessment: "
            f"{len(signals)} signal(s), overall level {overall_level.value}."
        )


__all__ = ["RiskCalculator"]
