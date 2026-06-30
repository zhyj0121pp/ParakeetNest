"""Provider-neutral valuation metric calculator."""

from __future__ import annotations

from parakeetnest.valuation.models import (
    ValuationInput,
    ValuationMetric,
    ValuationSnapshot,
)


class ValuationCalculator:
    """Calculate valuation metrics from normalized input values."""

    def calculate(self, valuation_input: ValuationInput) -> ValuationSnapshot:
        """Return a valuation snapshot with derived metrics and notes."""
        notes = list(valuation_input.calculation_notes)
        metrics = {
            ValuationMetric.PE_RATIO: self._divide(
                metric=ValuationMetric.PE_RATIO,
                numerator_name="market_cap",
                numerator=self._input_value(
                    valuation_input,
                    metric=ValuationMetric.MARKET_CAP,
                    assumption="market_cap",
                ),
                denominator_name="net_income",
                denominator=self._assumption_value(valuation_input, "net_income"),
                notes=notes,
            ),
            ValuationMetric.PS_RATIO: self._divide(
                metric=ValuationMetric.PS_RATIO,
                numerator_name="market_cap",
                numerator=self._input_value(
                    valuation_input,
                    metric=ValuationMetric.MARKET_CAP,
                    assumption="market_cap",
                ),
                denominator_name="revenue",
                denominator=self._assumption_value(valuation_input, "revenue"),
                notes=notes,
            ),
            ValuationMetric.PB_RATIO: self._divide(
                metric=ValuationMetric.PB_RATIO,
                numerator_name="market_cap",
                numerator=self._input_value(
                    valuation_input,
                    metric=ValuationMetric.MARKET_CAP,
                    assumption="market_cap",
                ),
                denominator_name="total_equity",
                denominator=self._assumption_value(valuation_input, "total_equity"),
                notes=notes,
            ),
            ValuationMetric.EV_TO_SALES: self._divide(
                metric=ValuationMetric.EV_TO_SALES,
                numerator_name="enterprise_value",
                numerator=self._input_value(
                    valuation_input,
                    metric=ValuationMetric.ENTERPRISE_VALUE,
                    assumption="enterprise_value",
                ),
                denominator_name="revenue",
                denominator=self._assumption_value(valuation_input, "revenue"),
                notes=notes,
            ),
            ValuationMetric.EV_TO_EBITDA: self._divide(
                metric=ValuationMetric.EV_TO_EBITDA,
                numerator_name="enterprise_value",
                numerator=self._input_value(
                    valuation_input,
                    metric=ValuationMetric.ENTERPRISE_VALUE,
                    assumption="enterprise_value",
                ),
                denominator_name="ebitda",
                denominator=self._assumption_value(valuation_input, "ebitda"),
                notes=notes,
            ),
            ValuationMetric.GROSS_MARGIN: self._divide(
                metric=ValuationMetric.GROSS_MARGIN,
                numerator_name="gross_profit",
                numerator=self._assumption_value(valuation_input, "gross_profit"),
                denominator_name="revenue",
                denominator=self._assumption_value(valuation_input, "revenue"),
                notes=notes,
            ),
            ValuationMetric.OPERATING_MARGIN: self._divide(
                metric=ValuationMetric.OPERATING_MARGIN,
                numerator_name="operating_income",
                numerator=self._assumption_value(valuation_input, "operating_income"),
                denominator_name="revenue",
                denominator=self._assumption_value(valuation_input, "revenue"),
                notes=notes,
            ),
            ValuationMetric.NET_MARGIN: self._divide(
                metric=ValuationMetric.NET_MARGIN,
                numerator_name="net_income",
                numerator=self._assumption_value(valuation_input, "net_income"),
                denominator_name="revenue",
                denominator=self._assumption_value(valuation_input, "revenue"),
                notes=notes,
            ),
            ValuationMetric.FREE_CASH_FLOW_YIELD: self._divide(
                metric=ValuationMetric.FREE_CASH_FLOW_YIELD,
                numerator_name="free_cash_flow",
                numerator=self._assumption_value(valuation_input, "free_cash_flow"),
                denominator_name="market_cap",
                denominator=self._input_value(
                    valuation_input,
                    metric=ValuationMetric.MARKET_CAP,
                    assumption="market_cap",
                ),
                notes=notes,
            ),
        }

        return ValuationSnapshot(
            symbol=valuation_input.symbol,
            as_of_date=valuation_input.as_of_date,
            metrics=metrics,
            fiscal_period=valuation_input.fiscal_period,
            data_sources=valuation_input.data_sources,
            calculation_notes=notes,
            confidence=valuation_input.confidence,
        )

    def _input_value(
        self,
        valuation_input: ValuationInput,
        *,
        metric: ValuationMetric,
        assumption: str,
    ) -> float | None:
        metric_value = self._number(valuation_input.metrics.get(metric))
        if metric_value is not None:
            return metric_value
        return self._assumption_value(valuation_input, assumption)

    def _assumption_value(
        self,
        valuation_input: ValuationInput,
        name: str,
    ) -> float | None:
        return self._number(valuation_input.assumptions.get(name))

    def _divide(
        self,
        *,
        metric: ValuationMetric,
        numerator_name: str,
        numerator: float | None,
        denominator_name: str,
        denominator: float | None,
        notes: list[str],
    ) -> float | None:
        missing = []
        if numerator is None:
            missing.append(numerator_name)
        if denominator is None:
            missing.append(denominator_name)

        if missing:
            notes.append(
                f"Skipped {metric.value}: missing {', '.join(missing)}.",
            )
            return None

        if denominator == 0:
            notes.append(
                f"Skipped {metric.value}: denominator {denominator_name} is zero.",
            )
            return None

        return numerator / denominator

    def _number(self, value: object) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        return None


__all__ = ["ValuationCalculator"]
