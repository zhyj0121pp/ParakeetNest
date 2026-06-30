"""Deterministic sector rotation calculations."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.sector_rotation.models import (
    MomentumSignal,
    RelativeStrengthSignal,
    SectorPerformance,
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)


class SectorRotationCalculator:
    """Calculate sector rotation snapshots from normalized performance facts."""

    def calculate(
        self,
        sector_performance: list[SectorPerformance],
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return a deterministic snapshot from normalized sector performance."""
        observed_on = as_of_date or self._infer_as_of_date(sector_performance)
        signals = [
            self._calculate_signal(performance, rank=index + 1)
            for index, performance in enumerate(
                sorted(
                    sector_performance,
                    key=self._relative_return_sort_key,
                )
            )
        ]

        return SectorRotationSnapshot(
            as_of_date=observed_on,
            signals=signals,
            summary=self._build_summary(signals),
            source="sector_rotation_calculator",
        )

    def _calculate_signal(
        self,
        performance: SectorPerformance,
        *,
        rank: int,
    ) -> SectorRotationSignal:
        classification = self._classify_relative_return(performance.relative_return)
        momentum_direction = self._classify_momentum(performance.period_return)
        confidence = self._confidence_for(performance)

        relative_strength = RelativeStrengthSignal(
            sector=performance.sector,
            score=performance.relative_return,
            rank=rank if performance.relative_return is not None else None,
            benchmark="broad_market",
            interpretation=self._relative_strength_interpretation(classification),
        )
        momentum = MomentumSignal(
            sector=performance.sector,
            score=performance.period_return,
            direction=momentum_direction,
            window_days=performance.window_days,
            interpretation=f"Sector momentum is {momentum_direction}.",
        )

        return SectorRotationSignal(
            sector=performance.sector,
            classification=classification,
            relative_strength=relative_strength,
            momentum=momentum,
            performance=performance,
            confidence=confidence,
            evidence=self._evidence_for(performance, classification, momentum_direction),
            risks=self._risks_for(classification, momentum_direction),
            catalysts=self._catalysts_for(classification, momentum_direction),
        )

    @staticmethod
    def _classify_relative_return(
        relative_return: float | None,
    ) -> SectorRotationClassification:
        if relative_return is None:
            return SectorRotationClassification.UNKNOWN
        if relative_return > 0.05:
            return SectorRotationClassification.LEADING
        if relative_return > 0:
            return SectorRotationClassification.IMPROVING
        if relative_return >= -0.05:
            return SectorRotationClassification.WEAKENING
        return SectorRotationClassification.LAGGING

    @staticmethod
    def _classify_momentum(period_return: float | None) -> str:
        if period_return is None or period_return == 0:
            return "flat"
        if period_return > 0:
            return "rising"
        return "falling"

    @staticmethod
    def _confidence_for(performance: SectorPerformance) -> str:
        if performance.relative_return is None:
            return "low"
        if performance.period_return is None or performance.benchmark_return is None:
            return "medium"
        return "high"

    @staticmethod
    def _relative_return_sort_key(performance: SectorPerformance) -> tuple[int, float, str]:
        if performance.relative_return is None:
            return (1, 0.0, performance.sector.name.lower())
        return (0, -performance.relative_return, performance.sector.name.lower())

    @staticmethod
    def _infer_as_of_date(sector_performance: list[SectorPerformance]) -> date:
        observed_dates = [
            performance.as_of_date
            for performance in sector_performance
            if performance.as_of_date is not None
        ]
        if observed_dates:
            return max(observed_dates)
        return date.today()

    @staticmethod
    def _relative_strength_interpretation(
        classification: SectorRotationClassification,
    ) -> str:
        match classification:
            case SectorRotationClassification.LEADING:
                return "Relative return is strongly positive."
            case SectorRotationClassification.IMPROVING:
                return "Relative return is positive."
            case SectorRotationClassification.WEAKENING:
                return "Relative return is modestly negative or flat."
            case SectorRotationClassification.LAGGING:
                return "Relative return is materially negative."
            case SectorRotationClassification.UNKNOWN:
                return "Relative return is unavailable."
            case SectorRotationClassification.NEUTRAL:
                return "Relative return is neutral."

    @staticmethod
    def _evidence_for(
        performance: SectorPerformance,
        classification: SectorRotationClassification,
        momentum_direction: str,
    ) -> tuple[str, ...]:
        evidence = [
            f"Relative return classified as {classification.value}.",
            f"Momentum classified as {momentum_direction}.",
        ]
        if performance.relative_return is not None:
            evidence.append(f"Relative return: {performance.relative_return:.4f}.")
        if performance.period_return is not None:
            evidence.append(f"Period return: {performance.period_return:.4f}.")
        return tuple(evidence)

    @staticmethod
    def _risks_for(
        classification: SectorRotationClassification,
        momentum_direction: str,
    ) -> tuple[str, ...]:
        risks: list[str] = []
        if classification in {
            SectorRotationClassification.WEAKENING,
            SectorRotationClassification.LAGGING,
        }:
            risks.append("Sector relative performance is deteriorating.")
        if momentum_direction == "falling":
            risks.append("Absolute momentum is falling.")
        if classification is SectorRotationClassification.UNKNOWN:
            risks.append("Relative performance evidence is incomplete.")
        return tuple(risks)

    @staticmethod
    def _catalysts_for(
        classification: SectorRotationClassification,
        momentum_direction: str,
    ) -> tuple[str, ...]:
        catalysts: list[str] = []
        if classification in {
            SectorRotationClassification.LEADING,
            SectorRotationClassification.IMPROVING,
        }:
            catalysts.append("Positive relative strength may attract rotation flows.")
        if momentum_direction == "rising":
            catalysts.append("Positive absolute momentum may support continued leadership.")
        return tuple(catalysts)

    @staticmethod
    def _build_summary(signals: list[SectorRotationSignal]) -> str:
        if not signals:
            return "No sector performance evidence available."
        leading_count = sum(
            signal.classification is SectorRotationClassification.LEADING
            for signal in signals
        )
        improving_count = sum(
            signal.classification is SectorRotationClassification.IMPROVING
            for signal in signals
        )
        weakening_count = sum(
            signal.classification is SectorRotationClassification.WEAKENING
            for signal in signals
        )
        lagging_count = sum(
            signal.classification is SectorRotationClassification.LAGGING
            for signal in signals
        )
        unknown_count = sum(
            signal.classification is SectorRotationClassification.UNKNOWN
            for signal in signals
        )
        return (
            "Calculated sector rotation snapshot: "
            f"{leading_count} leading, "
            f"{improving_count} improving, "
            f"{weakening_count} weakening, "
            f"{lagging_count} lagging, "
            f"{unknown_count} unknown."
        )


__all__ = ["SectorRotationCalculator"]
