"""Deterministic market health scoring and classification."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Mapping

from parakeetnest.intelligence.health.models import (
    HealthComponentState,
    MarketHealthComponent,
    MarketHealthSnapshot,
    MarketHealthState,
)


DEFAULT_WEIGHTS: Mapping[str, float] = {
    "economic_regime": 0.20,
    "risk": 0.20,
    "breadth": 0.20,
    "momentum": 0.20,
    "sentiment": 0.10,
    "sector_rotation": 0.10,
}


class MarketHealthCalculator:
    """Calculate market health snapshots from provider-neutral components."""

    def __init__(self, weights: Mapping[str, float] | None = None) -> None:
        """Initialize the calculator with optional component weights."""
        self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)

    def calculate(
        self,
        *,
        as_of: date,
        universe: str,
        components: tuple[MarketHealthComponent, ...] = (),
        economic_regime: Any | None = None,
        sector_rotation: Any | None = None,
        risk: Any | None = None,
        breadth: Any | None = None,
        momentum: Any | None = None,
        sentiment: Any | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MarketHealthSnapshot:
        """Return a deterministic composite health snapshot."""
        normalized_components = self.normalize_components(
            components
            + self.components_from_dependencies(
                economic_regime=economic_regime,
                sector_rotation=sector_rotation,
                risk=risk,
                breadth=breadth,
                momentum=momentum,
                sentiment=sentiment,
            )
        )
        health_score = self.calculate_score(normalized_components)
        confidence = self.confidence_for(normalized_components)
        health_state = (
            MarketHealthState.UNKNOWN
            if confidence == 0.0
            else self.classify_health(health_score)
        )

        return MarketHealthSnapshot(
            as_of=as_of,
            universe=universe,
            health_state=health_state,
            health_score=health_score,
            confidence=confidence,
            components=normalized_components,
            positives=self.positives_for(normalized_components),
            negatives=self.negatives_for(normalized_components),
            warnings=self.warnings_for(normalized_components),
            metadata=metadata or {},
        )

    def normalize_components(
        self,
        components: tuple[MarketHealthComponent, ...],
    ) -> tuple[MarketHealthComponent, ...]:
        """Apply default weights and normalized scores to usable components."""
        normalized: list[MarketHealthComponent] = []
        seen: set[str] = set()
        for component in components:
            if component.name in seen:
                continue
            seen.add(component.name)
            normalized.append(
                replace(
                    component,
                    score=self.score_for_component(component),
                    weight=self.weight_for(component),
                )
            )
        return tuple(normalized)

    def components_from_dependencies(
        self,
        *,
        economic_regime: Any | None = None,
        sector_rotation: Any | None = None,
        risk: Any | None = None,
        breadth: Any | None = None,
        momentum: Any | None = None,
        sentiment: Any | None = None,
    ) -> tuple[MarketHealthComponent, ...]:
        """Convert simplified dependency snapshots into neutral components."""
        raw = {
            "economic_regime": economic_regime,
            "sector_rotation": sector_rotation,
            "risk": risk,
            "breadth": breadth,
            "momentum": momentum,
            "sentiment": sentiment,
        }
        return tuple(
            self.component_from_snapshot(name, snapshot)
            for name, snapshot in raw.items()
            if snapshot is not None
        )

    def component_from_snapshot(
        self,
        name: str,
        snapshot: Any,
    ) -> MarketHealthComponent:
        """Build a component from common score/state fields on a snapshot."""
        score = self._extract_score(snapshot)
        state = self._state_from_snapshot(snapshot, score)
        evidence = self._extract_evidence(snapshot, name, state)
        return MarketHealthComponent(
            name=name,
            state=state,
            score=score,
            evidence=evidence,
        )

    def calculate_score(
        self,
        components: tuple[MarketHealthComponent, ...],
    ) -> float:
        """Return a weighted health score between 0.0 and 1.0."""
        usable = tuple(
            component
            for component in components
            if component.state is not HealthComponentState.UNKNOWN
            and component.score is not None
            and self.weight_for(component) > 0
        )
        total_weight = sum(self.weight_for(component) for component in usable)
        if total_weight <= 0:
            return 0.0

        weighted_score = sum(
            self._clamp_unit(component.score) * self.weight_for(component)
            for component in usable
        )
        return round(self._clamp_unit(weighted_score / total_weight), 4)

    @staticmethod
    def classify_health(score: float) -> MarketHealthState:
        """Return market health state for a normalized 0-1 score."""
        normalized_score = MarketHealthCalculator._clamp_unit(score)
        if normalized_score >= 0.80:
            return MarketHealthState.ROBUST
        if normalized_score >= 0.65:
            return MarketHealthState.HEALTHY
        if normalized_score >= 0.45:
            return MarketHealthState.FRAGILE
        if normalized_score >= 0.30:
            return MarketHealthState.DETERIORATING
        return MarketHealthState.STRESSED

    def confidence_for(
        self,
        components: tuple[MarketHealthComponent, ...],
    ) -> float:
        """Return confidence from availability of the default components."""
        available = {
            component.name
            for component in components
            if component.state is not HealthComponentState.UNKNOWN
            and component.score is not None
            and self.weight_for(component) > 0
        }
        possible = {name for name, weight in self.weights.items() if weight > 0}
        if not possible:
            return 0.0
        return round(self._clamp_unit(len(available & possible) / len(possible)), 4)

    @staticmethod
    def positives_for(
        components: tuple[MarketHealthComponent, ...],
    ) -> tuple[str, ...]:
        """Return deterministic positive component summaries."""
        return tuple(
            f"{component.name}: {MarketHealthCalculator._component_summary(component)}"
            for component in components
            if component.state is HealthComponentState.POSITIVE
        )

    @staticmethod
    def negatives_for(
        components: tuple[MarketHealthComponent, ...],
    ) -> tuple[str, ...]:
        """Return deterministic negative component summaries."""
        return tuple(
            f"{component.name}: {MarketHealthCalculator._component_summary(component)}"
            for component in components
            if component.state is HealthComponentState.NEGATIVE
        )

    @staticmethod
    def warnings_for(
        components: tuple[MarketHealthComponent, ...],
    ) -> tuple[str, ...]:
        """Return deterministic warning component summaries."""
        return tuple(
            f"{component.name}: {MarketHealthCalculator._component_summary(component)}"
            for component in components
            if component.state is HealthComponentState.WARNING
        )

    def weight_for(self, component: MarketHealthComponent) -> float:
        """Return the explicit or default weight for a component."""
        if component.weight is not None:
            return max(0.0, float(component.weight))
        return max(0.0, float(self.weights.get(component.name, 0.0)))

    @classmethod
    def score_for_component(cls, component: MarketHealthComponent) -> float | None:
        """Return a normalized score for a component."""
        if component.score is not None:
            return cls._clamp_unit(component.score)
        if component.state is HealthComponentState.POSITIVE:
            return 0.85
        if component.state is HealthComponentState.NEUTRAL:
            return 0.55
        if component.state is HealthComponentState.WARNING:
            return 0.35
        if component.state is HealthComponentState.NEGATIVE:
            return 0.15
        return None

    @classmethod
    def _state_from_snapshot(
        cls,
        snapshot: Any,
        score: float | None,
    ) -> HealthComponentState:
        raw_state = cls._extract_attr(snapshot, "state")
        if raw_state is None:
            raw_state = cls._extract_attr(snapshot, "health_state")
        if raw_state is None:
            raw_state = cls._extract_attr(snapshot, "regime")
        if raw_state is None:
            raw_state = cls._extract_attr(snapshot, "overall_level")
        if raw_state is not None:
            return cls._state_from_text(str(getattr(raw_state, "value", raw_state)))
        if score is None:
            return HealthComponentState.UNKNOWN
        if score >= 0.65:
            return HealthComponentState.POSITIVE
        if score >= 0.45:
            return HealthComponentState.NEUTRAL
        if score >= 0.30:
            return HealthComponentState.WARNING
        return HealthComponentState.NEGATIVE

    @classmethod
    def _state_from_text(cls, value: str) -> HealthComponentState:
        text = value.strip().lower()
        if text in {"positive", "expansion", "risk_on", "uptrend", "greed"}:
            return HealthComponentState.POSITIVE
        if text in {"neutral", "balanced", "mixed", "sideways"}:
            return HealthComponentState.NEUTRAL
        if text in {"warning", "fragile", "deteriorating", "elevated", "fear"}:
            return HealthComponentState.WARNING
        if text in {"negative", "contraction", "risk_off", "high", "extreme"}:
            return HealthComponentState.NEGATIVE
        if "strong_uptrend" in text or "healthy" in text or "robust" in text:
            return HealthComponentState.POSITIVE
        if "downtrend" in text or "stressed" in text or "extreme_fear" in text:
            return HealthComponentState.NEGATIVE
        if "fear" in text or "elevated" in text or "moderate" in text:
            return HealthComponentState.WARNING
        return HealthComponentState.UNKNOWN

    @classmethod
    def _extract_score(cls, snapshot: Any) -> float | None:
        for name in (
            "health_score",
            "overall_score",
            "momentum_score",
            "breadth_score",
            "rotation_score",
            "score",
        ):
            value = cls._extract_attr(snapshot, name)
            if value is None:
                continue
            score = float(value)
            if score > 1.0:
                score = score / 100
            return cls._clamp_unit(score)
        return None

    @staticmethod
    def _extract_attr(snapshot: Any, name: str) -> Any | None:
        if isinstance(snapshot, Mapping):
            return snapshot.get(name)
        return getattr(snapshot, name, None)

    @classmethod
    def _extract_evidence(
        cls,
        snapshot: Any,
        name: str,
        state: HealthComponentState,
    ) -> tuple[str, ...]:
        for field_name in ("evidence", "summary", "headline"):
            value = cls._extract_attr(snapshot, field_name)
            if isinstance(value, str) and value.strip():
                return (value.strip(),)
            if isinstance(value, (tuple, list)):
                evidence = tuple(str(item).strip() for item in value if str(item).strip())
                if evidence:
                    return evidence
        return (f"{name} component classified as {state.value}.",)

    @staticmethod
    def _component_summary(component: MarketHealthComponent) -> str:
        if component.evidence:
            return component.evidence[0]
        return f"component classified as {component.state.value}."

    @staticmethod
    def _clamp_unit(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


__all__ = ["DEFAULT_WEIGHTS", "MarketHealthCalculator"]
