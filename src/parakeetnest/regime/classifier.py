"""Rule-based economic regime classifier.

The classifier is intentionally deterministic and provider-neutral. It consumes
normalized point-in-time macro indicators, applies a small ordered rule set, and
returns an :class:`EconomicRegimeSnapshot` with the evidence used for the view.

Indicator values are expected to use percentage or percentage-point units:

- ``real_gdp_growth``: real GDP growth rate, percent.
- ``inflation_rate``: inflation rate, percent.
- ``unemployment_rate``: unemployment rate, percent.
- ``yield_curve_spread``: long minus short yield spread, percentage points.
- ``policy_rate``: central-bank policy rate, percent.
- ``credit_spread``: optional credit spread, percentage points.

Missing or invalid values are ignored. If the remaining evidence is not enough
to support a rule, the classifier returns ``UNKNOWN`` rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Callable

from parakeetnest.regime.models import (
    EconomicRegime,
    EconomicRegimeSnapshot,
    RegimeConfidence,
    RegimeIndicator,
    RegimeSignal,
)


@dataclass(frozen=True)
class _IndicatorSpec:
    """Validation and evidence metadata for one classifier input."""

    name: str
    signal: RegimeSignal
    unit: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class _Rule:
    """A single deterministic regime classification rule."""

    regime: EconomicRegime
    summary: str
    matches: Callable[[dict[str, float]], bool]


class EconomicRegimeClassifier:
    """Classify economic regimes from normalized macro indicators.

    The rules are ordered from most specific stress/transition states to broader
    benign states. This makes overlapping evidence deterministic: for example,
    high inflation with weak growth is classified as stagflation before it can
    fall through to slowdown.
    """

    source = "rule_based_economic_regime_classifier"

    _SPECS = {
        "real_gdp_growth": _IndicatorSpec(
            name="Real GDP Growth",
            signal=RegimeSignal.GROWTH,
            unit="percent",
            minimum=-30.0,
            maximum=30.0,
        ),
        "inflation_rate": _IndicatorSpec(
            name="Inflation Rate",
            signal=RegimeSignal.INFLATION,
            unit="percent",
            minimum=-10.0,
            maximum=30.0,
        ),
        "unemployment_rate": _IndicatorSpec(
            name="Unemployment Rate",
            signal=RegimeSignal.LABOR,
            unit="percent",
            minimum=0.0,
            maximum=40.0,
        ),
        "yield_curve_spread": _IndicatorSpec(
            name="Yield Curve Spread",
            signal=RegimeSignal.RATES,
            unit="percentage_point",
            minimum=-10.0,
            maximum=10.0,
        ),
        "policy_rate": _IndicatorSpec(
            name="Policy Rate",
            signal=RegimeSignal.RATES,
            unit="percent",
            minimum=0.0,
            maximum=30.0,
        ),
        "credit_spread": _IndicatorSpec(
            name="Credit Spread",
            signal=RegimeSignal.CREDIT,
            unit="percentage_point",
            minimum=0.0,
            maximum=40.0,
        ),
    }

    def __init__(self) -> None:
        """Initialize the default deterministic rule set."""
        self._rules = (
            _Rule(
                regime=EconomicRegime.STAGFLATION,
                summary=(
                    "Weak growth, elevated inflation, and labor-market stress "
                    "point to stagflation."
                ),
                matches=lambda values: (
                    values["real_gdp_growth"] <= 0.5
                    and values["inflation_rate"] >= 4.0
                    and values["unemployment_rate"] >= 5.0
                ),
            ),
            _Rule(
                regime=EconomicRegime.RECESSION,
                summary=(
                    "Negative growth and elevated unemployment point to "
                    "recession."
                ),
                matches=lambda values: (
                    values["real_gdp_growth"] < 0.0
                    and values["unemployment_rate"] >= 5.0
                    and values["inflation_rate"] < 4.0
                ),
            ),
            _Rule(
                regime=EconomicRegime.OVERHEATING,
                summary=(
                    "Strong growth, high inflation, and very tight labor "
                    "conditions point to overheating."
                ),
                matches=lambda values: (
                    values["real_gdp_growth"] >= 3.0
                    and values["inflation_rate"] >= 4.0
                    and values["unemployment_rate"] <= 4.0
                ),
            ),
            _Rule(
                regime=EconomicRegime.RECOVERY,
                summary=(
                    "Growth has turned positive while unemployment remains "
                    "elevated, consistent with recovery."
                ),
                matches=lambda values: (
                    0.5 <= values["real_gdp_growth"] < 2.5
                    and values["inflation_rate"] < 4.0
                    and values["unemployment_rate"] >= 5.0
                ),
            ),
            _Rule(
                regime=EconomicRegime.DISINFLATIONARY_GROWTH,
                summary=(
                    "Growth is positive, inflation is contained, and labor "
                    "conditions remain healthy."
                ),
                matches=lambda values: (
                    values["real_gdp_growth"] >= 1.5
                    and values["inflation_rate"] <= 2.5
                    and values["unemployment_rate"] <= 5.0
                ),
            ),
            _Rule(
                regime=EconomicRegime.EXPANSION,
                summary=(
                    "Growth is positive, inflation is moderate, and "
                    "unemployment is low."
                ),
                matches=lambda values: (
                    values["real_gdp_growth"] >= 2.0
                    and 1.5 <= values["inflation_rate"] < 4.0
                    and values["unemployment_rate"] <= 4.8
                ),
            ),
            _Rule(
                regime=EconomicRegime.SLOWDOWN,
                summary=(
                    "Growth is positive but subdued, with labor or rates "
                    "evidence pointing to cooling."
                ),
                matches=lambda values: (
                    0.0 <= values["real_gdp_growth"] < 1.5
                    and values["unemployment_rate"] < 5.0
                    and (
                        values["unemployment_rate"] >= 4.3
                        or values.get("yield_curve_spread", 1.0) <= 0.0
                        or values["inflation_rate"] >= 3.0
                    )
                ),
            ),
        )

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
        """Return a deterministic regime snapshot from normalized indicators.

        The three core indicators are growth, inflation, and unemployment. A
        classification needs all three because the initial rule set describes
        regimes by the interaction of activity, price pressure, and labor stress.
        Rates and credit values are retained as supporting evidence and can
        refine rules without changing the public API.
        """
        values = self._clean_values(
            {
                "real_gdp_growth": real_gdp_growth,
                "inflation_rate": inflation_rate,
                "unemployment_rate": unemployment_rate,
                "yield_curve_spread": yield_curve_spread,
                "policy_rate": policy_rate,
                "credit_spread": credit_spread,
            },
        )
        indicators = self._indicators(values, as_of_date=as_of_date)

        if not self._has_core_evidence(values):
            return EconomicRegimeSnapshot(
                regime=EconomicRegime.UNKNOWN,
                confidence=RegimeConfidence.UNKNOWN,
                indicators=indicators,
                summary=(
                    "Insufficient valid core macro evidence to classify the "
                    "economic regime."
                ),
                as_of_date=as_of_date or date.today(),
                source=self.source,
            )

        for rule in self._rules:
            if rule.matches(values):
                return EconomicRegimeSnapshot(
                    regime=rule.regime,
                    confidence=self._confidence(values),
                    indicators=indicators,
                    summary=rule.summary,
                    as_of_date=as_of_date or date.today(),
                    source=self.source,
                )

        return EconomicRegimeSnapshot(
            regime=EconomicRegime.UNKNOWN,
            confidence=RegimeConfidence.LOW,
            indicators=indicators,
            summary="Valid macro evidence does not match a supported regime rule.",
            as_of_date=as_of_date or date.today(),
            source=self.source,
        )

    def _clean_values(self, raw_values: dict[str, object | None]) -> dict[str, float]:
        """Return finite in-range numeric values keyed by indicator id."""
        values = {}
        for key, raw_value in raw_values.items():
            number = self._number(raw_value)
            if number is None:
                continue
            spec = self._SPECS[key]
            if spec.minimum <= number <= spec.maximum:
                values[key] = number
        return values

    def _number(self, value: object | None) -> float | None:
        """Convert plain numeric inputs to finite floats and reject invalid data."""
        if value is None or isinstance(value, bool):
            return None
        if not isinstance(value, int | float):
            return None
        number = float(value)
        if not isfinite(number):
            return None
        return number

    def _has_core_evidence(self, values: dict[str, float]) -> bool:
        """Return whether the rule set has enough evidence to make a call."""
        return {
            "real_gdp_growth",
            "inflation_rate",
            "unemployment_rate",
        }.issubset(values)

    def _confidence(self, values: dict[str, float]) -> RegimeConfidence:
        """Map breadth of valid evidence to a simple confidence level."""
        if len(values) >= 5:
            return RegimeConfidence.HIGH
        if len(values) >= 3:
            return RegimeConfidence.MEDIUM
        return RegimeConfidence.UNKNOWN

    def _indicators(
        self,
        values: dict[str, float],
        *,
        as_of_date: date | None,
    ) -> list[RegimeIndicator]:
        """Build sorted provider-neutral evidence indicators."""
        indicators = []
        for key, value in values.items():
            spec = self._SPECS[key]
            indicators.append(
                RegimeIndicator(
                    signal=spec.signal,
                    name=spec.name,
                    value=value,
                    unit=spec.unit,
                    as_of_date=as_of_date,
                    interpretation=self._interpretation(key, value),
                ),
            )
        return indicators

    def _interpretation(self, key: str, value: float) -> str:
        """Describe the rule-relevant meaning of one normalized indicator."""
        if key == "real_gdp_growth":
            if value < 0.0:
                return "contracting growth"
            if value < 1.5:
                return "subdued positive growth"
            if value >= 3.0:
                return "strong growth"
            return "positive growth"
        if key == "inflation_rate":
            if value <= 2.5:
                return "contained inflation"
            if value >= 4.0:
                return "elevated inflation"
            return "moderate inflation"
        if key == "unemployment_rate":
            if value <= 4.0:
                return "tight labor market"
            if value >= 5.0:
                return "elevated unemployment"
            return "moderate unemployment"
        if key == "yield_curve_spread":
            if value <= 0.0:
                return "inverted or flat yield curve"
            return "positively sloped yield curve"
        if key == "policy_rate":
            if value >= 4.0:
                return "restrictive policy rate"
            return "accommodative or neutral policy rate"
        if key == "credit_spread":
            if value >= 3.0:
                return "elevated credit stress"
            return "contained credit stress"
        return "supporting macro evidence"


__all__ = ["EconomicRegimeClassifier"]
