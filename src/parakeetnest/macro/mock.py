"""Deterministic in-memory macroeconomic data provider."""

from __future__ import annotations

from datetime import date

from parakeetnest.macro.models import (
    MacroCategory,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)
from parakeetnest.macro.provider import MacroDataProvider


class MockMacroDataProvider(MacroDataProvider):
    """Macro data provider backed by embedded deterministic fixtures."""

    _INDICATORS = {
        "fed_funds_rate": MacroIndicator(
            indicator_id="fed_funds_rate",
            name="Federal Funds Rate",
            category=MacroCategory.RATES,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Target policy rate proxy for local research workflows.",
        ),
        "treasury_10y_yield": MacroIndicator(
            indicator_id="treasury_10y_yield",
            name="10-Year Treasury Yield",
            category=MacroCategory.RATES,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Long-term sovereign yield proxy.",
        ),
        "cpi_yoy": MacroIndicator(
            indicator_id="cpi_yoy",
            name="CPI Year-over-Year",
            category=MacroCategory.INFLATION,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Headline consumer inflation proxy.",
        ),
        "core_cpi_yoy": MacroIndicator(
            indicator_id="core_cpi_yoy",
            name="Core CPI Year-over-Year",
            category=MacroCategory.INFLATION,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Core consumer inflation proxy.",
        ),
        "unemployment_rate": MacroIndicator(
            indicator_id="unemployment_rate",
            name="Unemployment Rate",
            category=MacroCategory.LABOR,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Labor market slack proxy.",
        ),
        "nonfarm_payrolls": MacroIndicator(
            indicator_id="nonfarm_payrolls",
            name="Nonfarm Payrolls",
            category=MacroCategory.LABOR,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.THOUSANDS,
            region="US",
            description="Monthly payroll employment change proxy.",
        ),
        "gdp_growth": MacroIndicator(
            indicator_id="gdp_growth",
            name="GDP Growth",
            category=MacroCategory.GROWTH,
            frequency=MacroFrequency.QUARTERLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Real output growth proxy.",
        ),
        "m2_growth": MacroIndicator(
            indicator_id="m2_growth",
            name="M2 Growth",
            category=MacroCategory.MONEY,
            frequency=MacroFrequency.MONTHLY,
            unit=MacroUnit.PERCENT,
            region="US",
            description="Broad money growth proxy.",
        ),
    }

    _OBSERVATIONS = {
        "fed_funds_rate": (
            MacroObservation(period=date(2026, 1, 31), value=4.50),
            MacroObservation(period=date(2026, 2, 28), value=4.50),
            MacroObservation(period=date(2026, 3, 31), value=4.25),
            MacroObservation(period=date(2026, 4, 30), value=4.25),
            MacroObservation(period=date(2026, 5, 31), value=4.00),
            MacroObservation(period=date(2026, 6, 30), value=4.00),
        ),
        "treasury_10y_yield": (
            MacroObservation(period=date(2026, 1, 31), value=4.18),
            MacroObservation(period=date(2026, 2, 28), value=4.11),
            MacroObservation(period=date(2026, 3, 31), value=4.05),
            MacroObservation(period=date(2026, 4, 30), value=4.22),
            MacroObservation(period=date(2026, 5, 31), value=4.17),
            MacroObservation(period=date(2026, 6, 30), value=4.08),
        ),
        "cpi_yoy": (
            MacroObservation(period=date(2026, 1, 31), value=3.20),
            MacroObservation(period=date(2026, 2, 28), value=3.10),
            MacroObservation(period=date(2026, 3, 31), value=3.00),
            MacroObservation(period=date(2026, 4, 30), value=2.90),
            MacroObservation(period=date(2026, 5, 31), value=2.80),
            MacroObservation(period=date(2026, 6, 30), value=2.70),
        ),
        "core_cpi_yoy": (
            MacroObservation(period=date(2026, 1, 31), value=3.50),
            MacroObservation(period=date(2026, 2, 28), value=3.40),
            MacroObservation(period=date(2026, 3, 31), value=3.30),
            MacroObservation(period=date(2026, 4, 30), value=3.20),
            MacroObservation(period=date(2026, 5, 31), value=3.10),
            MacroObservation(period=date(2026, 6, 30), value=3.00),
        ),
        "unemployment_rate": (
            MacroObservation(period=date(2026, 1, 31), value=4.10),
            MacroObservation(period=date(2026, 2, 28), value=4.10),
            MacroObservation(period=date(2026, 3, 31), value=4.20),
            MacroObservation(period=date(2026, 4, 30), value=4.20),
            MacroObservation(period=date(2026, 5, 31), value=4.30),
            MacroObservation(period=date(2026, 6, 30), value=4.30),
        ),
        "nonfarm_payrolls": (
            MacroObservation(period=date(2026, 1, 31), value=178.0),
            MacroObservation(period=date(2026, 2, 28), value=165.0),
            MacroObservation(period=date(2026, 3, 31), value=152.0),
            MacroObservation(period=date(2026, 4, 30), value=141.0),
            MacroObservation(period=date(2026, 5, 31), value=137.0),
            MacroObservation(period=date(2026, 6, 30), value=129.0),
        ),
        "gdp_growth": (
            MacroObservation(period=date(2025, 9, 30), value=2.40),
            MacroObservation(period=date(2025, 12, 31), value=2.20),
            MacroObservation(period=date(2026, 3, 31), value=2.00),
            MacroObservation(period=date(2026, 6, 30), value=1.90),
        ),
        "m2_growth": (
            MacroObservation(period=date(2026, 1, 31), value=2.10),
            MacroObservation(period=date(2026, 2, 28), value=2.30),
            MacroObservation(period=date(2026, 3, 31), value=2.60),
            MacroObservation(period=date(2026, 4, 30), value=2.80),
            MacroObservation(period=date(2026, 5, 31), value=3.00),
            MacroObservation(period=date(2026, 6, 30), value=3.10),
        ),
    }

    def get_series(
        self,
        indicator_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MacroSeries:
        """Return deterministic observations for the requested indicator."""
        normalized_id = indicator_id.strip().lower()
        indicator = self._INDICATORS.get(normalized_id)
        if indicator is None:
            return MacroSeries(indicator=self._unknown_indicator(normalized_id))

        observations = [
            observation
            for observation in self._OBSERVATIONS[indicator.indicator_id]
            if (start_date is None or observation.period >= start_date)
            and (end_date is None or observation.period <= end_date)
        ]
        return MacroSeries(indicator=indicator, observations=observations)

    def get_latest(self, indicator_id: str) -> MacroObservation | None:
        """Return the latest available observation for a known indicator."""
        series = self.get_series(indicator_id)
        if not series.observations:
            return None
        return series.observations[-1]

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Return a deterministic point-in-time macro snapshot."""
        snapshot_date = as_of_date or self._latest_fixture_date()
        return MacroSnapshot(
            as_of_date=snapshot_date,
            series=[
                self.get_series(indicator_id, end_date=snapshot_date)
                for indicator_id in indicator_ids
            ],
        )

    def _latest_fixture_date(self) -> date:
        latest_dates = (
            observations[-1].period
            for observations in self._OBSERVATIONS.values()
            if observations
        )
        return max(latest_dates)

    def _unknown_indicator(self, indicator_id: str) -> MacroIndicator:
        fallback_id = indicator_id or "unknown_indicator"
        return MacroIndicator(
            indicator_id=fallback_id,
            name=fallback_id.replace("_", " ").title(),
            category=MacroCategory.OTHER,
            frequency=MacroFrequency.IRREGULAR,
            unit=MacroUnit.OTHER,
        )


__all__ = ["MockMacroDataProvider"]
