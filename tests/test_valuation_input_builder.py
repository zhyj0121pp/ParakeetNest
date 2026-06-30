"""Tests for valuation input normalization from context snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from parakeetnest.context import (
    ContextRequest,
    FinancialStatementItem,
    FinancialStatementSnapshot,
    MarketDataPoint,
    MarketSnapshot,
)
from parakeetnest.valuation import (
    ValuationConfidence,
    ValuationInputBuilder,
    ValuationMethod,
    ValuationMetric,
)


@dataclass(frozen=True)
class MarketPointWithEnterpriseValue:
    symbol: str
    source: str
    market_cap: float | None = None
    enterprise_value: float | None = None


@dataclass(frozen=True)
class FinancialItemWithEbitda:
    symbol: str
    period_type: str
    source: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    total_equity: float | None = None
    ebitda: float | None = None
    free_cash_flow: float | None = None
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None


def test_valuation_input_builder_extracts_normalized_context_inputs() -> None:
    """Builder should convert normalized context into valuation input fields."""
    request = ContextRequest(
        question="Review AMD.",
        symbols=("AMD",),
        as_of=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
    )
    market = MarketSnapshot(
        source="market_context",
        fetched_at=request.as_of,
        points=(
            MarketDataPoint(symbol="NVDA", source="market_context", market_cap=300.0),
            MarketPointWithEnterpriseValue(
                symbol="amd",
                source="normalized_market",
                market_cap=1_000.0,
                enterprise_value=1_100.0,
            ),
        ),
    )
    financials = FinancialStatementSnapshot(
        source="financial_context",
        fetched_at=request.as_of,
        items=(
            FinancialStatementItem(
                symbol="NVDA",
                period_type="ttm",
                source="normalized_financials",
                revenue=300.0,
            ),
            FinancialItemWithEbitda(
                symbol="AMD",
                period_type="quarterly",
                source="normalized_financials",
                revenue=100.0,
                gross_profit=60.0,
                operating_income=25.0,
                net_income=20.0,
                total_equity=400.0,
                ebitda=30.0,
                free_cash_flow=18.0,
                fiscal_year=2026,
                fiscal_quarter=2,
            ),
        ),
    )

    valuation_input = ValuationInputBuilder().build(
        " amd ",
        request,
        market,
        financials,
    )

    assert valuation_input.symbol == "AMD"
    assert valuation_input.method is ValuationMethod.HISTORICAL_MULTIPLES
    assert valuation_input.as_of_date == date(2026, 6, 29)
    assert valuation_input.fiscal_period == "FY2026Q2"
    assert valuation_input.metrics == {
        ValuationMetric.MARKET_CAP: 1_000.0,
        ValuationMetric.ENTERPRISE_VALUE: 1_100.0,
    }
    assert valuation_input.assumptions == {
        "revenue": 100.0,
        "gross_profit": 60.0,
        "operating_income": 25.0,
        "net_income": 20.0,
        "total_equity": 400.0,
        "free_cash_flow": 18.0,
        "ebitda": 30.0,
    }
    assert valuation_input.data_sources == [
        "market_context",
        "normalized_market",
        "financial_context",
        "normalized_financials",
    ]
    assert valuation_input.calculation_notes == [
        "Valuation inputs normalized from context snapshots."
    ]
    assert valuation_input.confidence is ValuationConfidence.HIGH


def test_valuation_input_builder_handles_missing_snapshots() -> None:
    """Missing context should produce an empty low-confidence input."""
    request = ContextRequest(question="Review AAPL.", symbols=("AAPL",))

    valuation_input = ValuationInputBuilder(method=ValuationMethod.OWNER_EARNINGS)(
        "AAPL",
        request,
    )

    assert valuation_input.symbol == "AAPL"
    assert valuation_input.method is ValuationMethod.OWNER_EARNINGS
    assert valuation_input.metrics == {}
    assert valuation_input.assumptions == {}
    assert valuation_input.fiscal_period is None
    assert valuation_input.data_sources == []
    assert valuation_input.confidence is ValuationConfidence.LOW
    assert (
        "No market snapshot data matched the requested symbol."
        in valuation_input.calculation_notes
    )
    assert (
        "No financial statement snapshot data matched the requested symbol."
        in valuation_input.calculation_notes
    )


def test_valuation_input_builder_is_provider_neutral() -> None:
    """Builder must only depend on normalized context, not provider APIs."""
    request = ContextRequest(
        question="Review MSFT.",
        symbols=("MSFT",),
        as_of=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
    )
    market = MarketSnapshot(
        source="provider_a",
        points=(MarketDataPoint(symbol="MSFT", source="provider_a", market_cap=50.0),),
    )

    valuation_input = ValuationInputBuilder().build(
        "MSFT",
        request,
        market=market,
        financials=None,
    )

    assert valuation_input.metrics == {ValuationMetric.MARKET_CAP: 50.0}
    assert valuation_input.assumptions == {}
    assert valuation_input.confidence is ValuationConfidence.MEDIUM
    assert "yahoo" not in repr(valuation_input).lower()
    assert "sec" not in repr(valuation_input).lower()
