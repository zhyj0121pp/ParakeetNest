"""Provider-neutral service boundary for economic regime classification."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Protocol

from parakeetnest.macro.models import MacroSnapshot
from parakeetnest.regime.classifier import EconomicRegimeClassifier
from parakeetnest.regime.models import (
    EconomicRegime,
    EconomicRegimeSnapshot,
    RegimeConfidence,
)


class _MacroService(Protocol):
    """Minimal macro service contract consumed by the regime service."""

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Return a normalized macro snapshot."""


class _RegimeClassifier(Protocol):
    """Minimal classifier contract consumed by the service layer."""

    def classify(
        self,
        *,
        real_gdp_growth: object | None = None,
        inflation_rate: object | None = None,
        unemployment_rate: object | None = None,
        yield_curve_spread: object | None = None,
        policy_rate: object | None = None,
        credit_spread: object | None = None,
        as_of_date: date | None = None,
    ) -> EconomicRegimeSnapshot:
        """Classify a regime from normalized macro values."""


class EconomicRegimeService:
    """Public service layer for provider-neutral regime classification."""

    DEFAULT_INDICATOR_MAP: Mapping[str, str] = {
        "real_gdp_growth": "gdp_growth",
        "inflation_rate": "cpi_yoy",
        "unemployment_rate": "unemployment_rate",
        "yield_curve_spread": "yield_curve_spread",
        "policy_rate": "fed_funds_rate",
        "credit_spread": "credit_spread",
    }

    def __init__(
        self,
        macro_service: _MacroService,
        classifier: _RegimeClassifier | None = None,
        indicator_map: Mapping[str, str] | None = None,
    ) -> None:
        """Initialize the service with macro and classifier abstractions."""
        self._macro_service = macro_service
        self._classifier = classifier or EconomicRegimeClassifier()
        self._indicator_map = dict(indicator_map or self.DEFAULT_INDICATOR_MAP)

    def get_current_regime(
        self,
        *,
        as_of_date: date | None = None,
        indicator_map: Mapping[str, str] | None = None,
    ) -> EconomicRegimeSnapshot:
        """Retrieve normalized macro data and classify the current regime."""
        active_map = self._active_indicator_map(indicator_map)
        try:
            macro_snapshot = self._macro_service.get_snapshot(
                list(active_map.values()),
                as_of_date=as_of_date,
            )
        except Exception:
            return self._unknown_snapshot(
                as_of_date=as_of_date,
                summary=(
                    "Unable to retrieve normalized macro data for regime "
                    "classification."
                ),
            )

        return self.classify_snapshot(macro_snapshot, indicator_map=active_map)

    def classify_snapshot(
        self,
        macro_snapshot: MacroSnapshot,
        *,
        indicator_map: Mapping[str, str] | None = None,
    ) -> EconomicRegimeSnapshot:
        """Classify a provider-neutral macro snapshot."""
        active_map = self._active_indicator_map(indicator_map)
        values = self._classifier_inputs(macro_snapshot, active_map)
        return self._classifier.classify(
            real_gdp_growth=values.get("real_gdp_growth"),
            inflation_rate=values.get("inflation_rate"),
            unemployment_rate=values.get("unemployment_rate"),
            yield_curve_spread=values.get("yield_curve_spread"),
            policy_rate=values.get("policy_rate"),
            credit_spread=values.get("credit_spread"),
            as_of_date=macro_snapshot.as_of_date,
        )

    def _active_indicator_map(
        self,
        indicator_map: Mapping[str, str] | None,
    ) -> dict[str, str]:
        """Return the caller-provided map or the service default."""
        return dict(indicator_map or self._indicator_map)

    def _classifier_inputs(
        self,
        macro_snapshot: MacroSnapshot,
        indicator_map: Mapping[str, str],
    ) -> dict[str, float | None]:
        """Extract latest normalized observations for classifier input names."""
        latest_values = {}
        for series in macro_snapshot.series:
            if not series.observations:
                continue
            latest_values[series.indicator.indicator_id] = series.observations[-1].value

        return {
            classifier_input: latest_values.get(macro_indicator_id)
            for classifier_input, macro_indicator_id in indicator_map.items()
        }

    def _unknown_snapshot(
        self,
        *,
        as_of_date: date | None,
        summary: str,
    ) -> EconomicRegimeSnapshot:
        """Return a neutral snapshot when macro data cannot be obtained."""
        return EconomicRegimeSnapshot(
            regime=EconomicRegime.UNKNOWN,
            confidence=RegimeConfidence.UNKNOWN,
            as_of_date=as_of_date or date.today(),
            summary=summary,
            source="economic_regime_service",
        )


__all__ = ["EconomicRegimeService"]
