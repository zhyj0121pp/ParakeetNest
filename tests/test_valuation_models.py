"""Tests for Valuation Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from parakeetnest.valuation import (
    ValuationConfidence,
    ValuationInput,
    ValuationMethod,
    ValuationMetric,
    ValuationSnapshot,
)


def test_valuation_metric_values_are_provider_agnostic() -> None:
    """Common valuation metrics should expose stable string values."""
    assert ValuationMetric.MARKET_CAP.value == "market_cap"
    assert ValuationMetric.ENTERPRISE_VALUE.value == "enterprise_value"
    assert ValuationMetric.PE_RATIO.value == "pe_ratio"
    assert ValuationMetric.FORWARD_PE_RATIO.value == "forward_pe_ratio"
    assert ValuationMetric.PS_RATIO.value == "ps_ratio"
    assert ValuationMetric.PB_RATIO.value == "pb_ratio"
    assert ValuationMetric.EV_TO_SALES.value == "ev_to_sales"
    assert ValuationMetric.EV_TO_EBITDA.value == "ev_to_ebitda"
    assert ValuationMetric.GROSS_MARGIN.value == "gross_margin"
    assert ValuationMetric.OPERATING_MARGIN.value == "operating_margin"
    assert ValuationMetric.NET_MARGIN.value == "net_margin"
    assert ValuationMetric.REVENUE_GROWTH.value == "revenue_growth"
    assert ValuationMetric.EPS_GROWTH.value == "eps_growth"
    assert ValuationMetric.FREE_CASH_FLOW_YIELD.value == "free_cash_flow_yield"


def test_valuation_method_values_are_provider_neutral() -> None:
    """Valuation methods should describe approaches, not providers."""
    assert ValuationMethod.COMPARABLE_COMPANIES.value == "comparable_companies"
    assert ValuationMethod.DISCOUNTED_CASH_FLOW.value == "discounted_cash_flow"
    assert ValuationMethod.HISTORICAL_MULTIPLES.value == "historical_multiples"
    assert ValuationMethod.SUM_OF_THE_PARTS.value == "sum_of_the_parts"
    assert ValuationMethod.ASSET_BASED.value == "asset_based"
    assert ValuationMethod.OWNER_EARNINGS.value == "owner_earnings"


def test_valuation_confidence_values_are_stable() -> None:
    """Confidence should be encoded independently from any provider scoring."""
    assert ValuationConfidence.LOW.value == "low"
    assert ValuationConfidence.MEDIUM.value == "medium"
    assert ValuationConfidence.HIGH.value == "high"
    assert ValuationConfidence.UNKNOWN.value == "unknown"


def test_valuation_snapshot_normalizes_metadata_and_metrics() -> None:
    """A snapshot should capture source metadata and normalized metrics."""
    snapshot = ValuationSnapshot(
        symbol=" nvda ",
        as_of_date=date(2026, 6, 29),
        fiscal_period="FY2026",
        metrics={
            "market_cap": 4_000_000_000_000.0,
            ValuationMetric.FORWARD_PE_RATIO: 33.5,
            "free_cash_flow_yield": None,
        },
        data_sources=[" yahoo ", "", " company filing "],
        calculation_notes=[" trailing values use ttm ", ""],
        confidence="high",
    )

    assert snapshot.symbol == "NVDA"
    assert snapshot.as_of_date == date(2026, 6, 29)
    assert snapshot.fiscal_period == "FY2026"
    assert snapshot.metrics == {
        ValuationMetric.MARKET_CAP: 4_000_000_000_000.0,
        ValuationMetric.FORWARD_PE_RATIO: 33.5,
        ValuationMetric.FREE_CASH_FLOW_YIELD: None,
    }
    assert snapshot.data_sources == ["yahoo", "company filing"]
    assert snapshot.calculation_notes == ["trailing values use ttm"]
    assert snapshot.confidence is ValuationConfidence.HIGH

    with pytest.raises(FrozenInstanceError):
        snapshot.symbol = "AMD"


def test_valuation_snapshot_defaults_are_empty_provider_neutral_metadata() -> None:
    """Optional source metadata should default to empty provider-neutral values."""
    snapshot = ValuationSnapshot(
        symbol="AAPL",
        as_of_date=date(2026, 6, 29),
    )

    assert snapshot.metrics == {}
    assert snapshot.fiscal_period is None
    assert snapshot.data_sources == []
    assert snapshot.calculation_notes == []
    assert snapshot.confidence is ValuationConfidence.UNKNOWN


def test_valuation_input_normalizes_method_metrics_and_assumptions() -> None:
    """Inputs should prepare clean data for future valuation engines."""
    valuation_input = ValuationInput(
        symbol=" msft ",
        method="discounted_cash_flow",
        as_of_date=date(2026, 6, 29),
        fiscal_period="TTM",
        metrics={
            "enterprise_value": 3_900_000_000_000.0,
            "ev_to_sales": 12.0,
            ValuationMetric.NET_MARGIN: 0.36,
        },
        assumptions={" discount_rate ": 0.09, "": 1.0, "terminal_growth": 0.03},
        data_sources=[" financial statements ", " market snapshot "],
        calculation_notes=["FCF normalized for one-time charges"],
        confidence=ValuationConfidence.MEDIUM,
    )

    assert valuation_input.symbol == "MSFT"
    assert valuation_input.method is ValuationMethod.DISCOUNTED_CASH_FLOW
    assert valuation_input.as_of_date == date(2026, 6, 29)
    assert valuation_input.fiscal_period == "TTM"
    assert valuation_input.metrics == {
        ValuationMetric.ENTERPRISE_VALUE: 3_900_000_000_000.0,
        ValuationMetric.EV_TO_SALES: 12.0,
        ValuationMetric.NET_MARGIN: 0.36,
    }
    assert valuation_input.assumptions == {
        "discount_rate": 0.09,
        "terminal_growth": 0.03,
    }
    assert valuation_input.data_sources == [
        "financial statements",
        "market snapshot",
    ]
    assert valuation_input.calculation_notes == [
        "FCF normalized for one-time charges",
    ]
    assert valuation_input.confidence is ValuationConfidence.MEDIUM


def test_invalid_metric_method_and_confidence_values_are_rejected() -> None:
    """Unknown values should fail early before reaching valuation engines."""
    with pytest.raises(ValueError):
        ValuationSnapshot(
            symbol="AAPL",
            as_of_date=date(2026, 6, 29),
            metrics={"provider_specific_metric": 1.0},
        )

    with pytest.raises(ValueError):
        ValuationInput(
            symbol="AAPL",
            method="provider_magic_model",
            as_of_date=date(2026, 6, 29),
        )

    with pytest.raises(ValueError):
        ValuationSnapshot(
            symbol="AAPL",
            as_of_date=date(2026, 6, 29),
            confidence="certain",
        )
