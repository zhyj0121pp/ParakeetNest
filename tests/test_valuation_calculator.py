"""Tests for provider-neutral valuation calculations."""

from __future__ import annotations

from datetime import date

import pytest

from parakeetnest.valuation import (
    ValuationCalculator,
    ValuationConfidence,
    ValuationInput,
    ValuationMethod,
    ValuationMetric,
)


def test_valuation_calculator_derives_supported_metrics() -> None:
    """Calculator should derive ratios from normalized market and statement data."""
    calculator = ValuationCalculator()
    valuation_input = ValuationInput(
        symbol=" nvda ",
        method=ValuationMethod.HISTORICAL_MULTIPLES,
        as_of_date=date(2026, 6, 29),
        fiscal_period="TTM",
        metrics={
            ValuationMetric.MARKET_CAP: 3_000.0,
            ValuationMetric.ENTERPRISE_VALUE: 3_200.0,
        },
        assumptions={
            "revenue": 100.0,
            "gross_profit": 70.0,
            "operating_income": 45.0,
            "net_income": 30.0,
            "total_equity": 500.0,
            "ebitda": 50.0,
            "free_cash_flow": 24.0,
        },
        data_sources=["market snapshot", "financial statements"],
        calculation_notes=["Inputs normalized from latest statements."],
        confidence=ValuationConfidence.HIGH,
    )

    snapshot = calculator.calculate(valuation_input)

    assert snapshot.symbol == "NVDA"
    assert snapshot.as_of_date == date(2026, 6, 29)
    assert snapshot.fiscal_period == "TTM"
    assert snapshot.data_sources == ["market snapshot", "financial statements"]
    assert snapshot.calculation_notes == [
        "Inputs normalized from latest statements.",
    ]
    assert snapshot.confidence is ValuationConfidence.HIGH
    assert snapshot.metrics[ValuationMetric.PE_RATIO] == pytest.approx(100.0)
    assert snapshot.metrics[ValuationMetric.PS_RATIO] == pytest.approx(30.0)
    assert snapshot.metrics[ValuationMetric.PB_RATIO] == pytest.approx(6.0)
    assert snapshot.metrics[ValuationMetric.EV_TO_SALES] == pytest.approx(32.0)
    assert snapshot.metrics[ValuationMetric.EV_TO_EBITDA] == pytest.approx(64.0)
    assert snapshot.metrics[ValuationMetric.GROSS_MARGIN] == pytest.approx(0.7)
    assert snapshot.metrics[ValuationMetric.OPERATING_MARGIN] == pytest.approx(0.45)
    assert snapshot.metrics[ValuationMetric.NET_MARGIN] == pytest.approx(0.3)
    assert snapshot.metrics[ValuationMetric.FREE_CASH_FLOW_YIELD] == pytest.approx(
        0.008,
    )


def test_valuation_calculator_skips_missing_inputs_with_notes() -> None:
    """Missing numerator or denominator inputs should produce None and notes."""
    snapshot = ValuationCalculator().calculate(
        ValuationInput(
            symbol="AAPL",
            method=ValuationMethod.HISTORICAL_MULTIPLES,
            as_of_date=date(2026, 6, 29),
            metrics={ValuationMetric.MARKET_CAP: 1_000.0},
            assumptions={
                "revenue": 100.0,
                "net_income": 25.0,
            },
        ),
    )

    assert snapshot.metrics[ValuationMetric.PE_RATIO] == pytest.approx(40.0)
    assert snapshot.metrics[ValuationMetric.PS_RATIO] == pytest.approx(10.0)
    assert snapshot.metrics[ValuationMetric.PB_RATIO] is None
    assert snapshot.metrics[ValuationMetric.EV_TO_SALES] is None
    assert snapshot.metrics[ValuationMetric.GROSS_MARGIN] is None
    assert "Skipped pb_ratio: missing total_equity." in snapshot.calculation_notes
    assert (
        "Skipped ev_to_sales: missing enterprise_value."
        in snapshot.calculation_notes
    )
    assert (
        "Skipped gross_margin: missing gross_profit." in snapshot.calculation_notes
    )


def test_valuation_calculator_skips_zero_denominators_with_notes() -> None:
    """Zero denominators should not raise or produce infinite values."""
    snapshot = ValuationCalculator().calculate(
        ValuationInput(
            symbol="MSFT",
            method=ValuationMethod.HISTORICAL_MULTIPLES,
            as_of_date=date(2026, 6, 29),
            metrics={
                ValuationMetric.MARKET_CAP: 1_000.0,
                ValuationMetric.ENTERPRISE_VALUE: 1_200.0,
            },
            assumptions={
                "revenue": 0.0,
                "gross_profit": 20.0,
                "operating_income": 10.0,
                "net_income": 0.0,
                "total_equity": 0.0,
                "ebitda": 0.0,
                "free_cash_flow": 50.0,
            },
        ),
    )

    assert snapshot.metrics[ValuationMetric.PE_RATIO] is None
    assert snapshot.metrics[ValuationMetric.PS_RATIO] is None
    assert snapshot.metrics[ValuationMetric.PB_RATIO] is None
    assert snapshot.metrics[ValuationMetric.EV_TO_EBITDA] is None
    assert snapshot.metrics[ValuationMetric.GROSS_MARGIN] is None
    assert snapshot.metrics[ValuationMetric.FREE_CASH_FLOW_YIELD] == pytest.approx(
        0.05,
    )
    assert (
        "Skipped pe_ratio: denominator net_income is zero."
        in snapshot.calculation_notes
    )
    assert (
        "Skipped ev_to_ebitda: denominator ebitda is zero."
        in snapshot.calculation_notes
    )
    assert (
        "Skipped gross_margin: denominator revenue is zero."
        in snapshot.calculation_notes
    )
