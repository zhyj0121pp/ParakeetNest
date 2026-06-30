"""Tests for Financial Statement Layer domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from parakeetnest.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementRequest,
    IncomeStatement,
)


def test_financial_period_type_values_are_provider_agnostic() -> None:
    """Supported statement period types should expose stable string values."""
    assert FinancialPeriodType.ANNUAL.value == "annual"
    assert FinancialPeriodType.QUARTERLY.value == "quarterly"
    assert FinancialPeriodType.TRAILING_TWELVE_MONTHS.value == "ttm"


def test_financial_statement_period_creation_normalizes_fields() -> None:
    """Financial periods should carry normalized provider-neutral metadata."""
    period = FinancialStatementPeriod(
        symbol=" aapl ",
        period_type="quarterly",
        fiscal_year=2026,
        fiscal_quarter=2,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        report_date=date(2026, 4, 30),
        currency=" usd ",
    )

    assert period.symbol == "AAPL"
    assert period.period_type is FinancialPeriodType.QUARTERLY
    assert period.fiscal_year == 2026
    assert period.fiscal_quarter == 2
    assert period.start_date == date(2026, 1, 1)
    assert period.end_date == date(2026, 3, 31)
    assert period.report_date == date(2026, 4, 30)
    assert period.currency == "USD"

    with pytest.raises(FrozenInstanceError):
        period.symbol = "MSFT"


def test_income_statement_creation() -> None:
    """An income statement should capture common profit and per-share fields."""
    retrieved_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    period = FinancialStatementPeriod(
        symbol="NVDA",
        period_type=FinancialPeriodType.ANNUAL,
        fiscal_year=2026,
        currency="USD",
    )
    statement = IncomeStatement(
        period=period,
        revenue=130_497_000_000.0,
        cost_of_revenue=32_639_000_000.0,
        gross_profit=97_858_000_000.0,
        operating_income=81_453_000_000.0,
        net_income=72_880_000_000.0,
        eps_basic=2.97,
        eps_diluted=2.94,
        shares_basic=24_500_000_000.0,
        shares_diluted=24_800_000_000.0,
        source="mock",
        retrieved_at=retrieved_at,
    )

    assert statement.period == period
    assert statement.revenue == 130_497_000_000.0
    assert statement.net_income == 72_880_000_000.0
    assert statement.eps_diluted == 2.94
    assert statement.source == "mock"
    assert statement.retrieved_at == retrieved_at


def test_balance_sheet_creation() -> None:
    """A balance sheet should capture common asset, liability, and debt fields."""
    period = FinancialStatementPeriod(
        symbol="MSFT",
        period_type=FinancialPeriodType.QUARTERLY,
        fiscal_year=2026,
        fiscal_quarter=3,
    )
    statement = BalanceSheet(
        period=period,
        total_assets=619_000_000_000.0,
        total_liabilities=243_000_000_000.0,
        total_equity=376_000_000_000.0,
        cash_and_equivalents=80_000_000_000.0,
        short_term_investments=20_000_000_000.0,
        total_debt=60_000_000_000.0,
        current_assets=190_000_000_000.0,
        current_liabilities=125_000_000_000.0,
    )

    assert statement.period == period
    assert statement.total_assets == 619_000_000_000.0
    assert statement.total_liabilities == 243_000_000_000.0
    assert statement.total_equity == 376_000_000_000.0
    assert statement.current_liabilities == 125_000_000_000.0


def test_cash_flow_statement_creation() -> None:
    """A cash flow statement should capture common cash movement fields."""
    period = FinancialStatementPeriod(
        symbol="AMZN",
        period_type=FinancialPeriodType.TRAILING_TWELVE_MONTHS,
        fiscal_year=2026,
    )
    statement = CashFlowStatement(
        period=period,
        operating_cash_flow=120_000_000_000.0,
        investing_cash_flow=-75_000_000_000.0,
        financing_cash_flow=-10_000_000_000.0,
        capital_expenditures=-60_000_000_000.0,
        free_cash_flow=60_000_000_000.0,
        depreciation_and_amortization=45_000_000_000.0,
        stock_based_compensation=23_000_000_000.0,
    )

    assert statement.period == period
    assert statement.operating_cash_flow == 120_000_000_000.0
    assert statement.capital_expenditures == -60_000_000_000.0
    assert statement.free_cash_flow == 60_000_000_000.0
    assert statement.stock_based_compensation == 23_000_000_000.0


def test_financial_statement_bundle_groups_statements() -> None:
    """A bundle should group the three statement types for one symbol."""
    retrieved_at = datetime(2026, 6, 29, 12, 30, tzinfo=UTC)
    period = FinancialStatementPeriod(
        symbol="meta",
        period_type=FinancialPeriodType.ANNUAL,
        fiscal_year=2026,
    )
    income_statement = IncomeStatement(period=period, revenue=180_000_000_000.0)
    balance_sheet = BalanceSheet(period=period, total_assets=300_000_000_000.0)
    cash_flow_statement = CashFlowStatement(
        period=period,
        free_cash_flow=55_000_000_000.0,
    )
    bundle = FinancialStatementBundle(
        symbol=" meta ",
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        cash_flow_statement=cash_flow_statement,
        source="mock",
        retrieved_at=retrieved_at,
    )

    assert bundle.symbol == "META"
    assert bundle.income_statement == income_statement
    assert bundle.balance_sheet == balance_sheet
    assert bundle.cash_flow_statement == cash_flow_statement
    assert bundle.source == "mock"
    assert bundle.retrieved_at == retrieved_at


def test_financial_statement_request_defaults_and_normalization() -> None:
    """A request should default to a small provider-neutral statement request."""
    request = FinancialStatementRequest(symbol=" tsla ", period_type="annual")

    assert request.symbol == "TSLA"
    assert request.period_type is FinancialPeriodType.ANNUAL
    assert request.limit == 4


def test_financial_statement_request_rejects_non_positive_limit() -> None:
    """Requests should keep provider calls bounded to positive result counts."""
    with pytest.raises(ValueError, match="limit must be at least 1"):
        FinancialStatementRequest(
            symbol="AAPL",
            period_type=FinancialPeriodType.QUARTERLY,
            limit=0,
        )


def test_optional_fields_can_be_none() -> None:
    """Statement fields should allow unavailable accounting values."""
    period = FinancialStatementPeriod(
        symbol="AAPL",
        period_type=FinancialPeriodType.QUARTERLY,
        fiscal_year=2026,
    )

    income_statement = IncomeStatement(period=period)
    balance_sheet = BalanceSheet(period=period)
    cash_flow_statement = CashFlowStatement(period=period)
    bundle = FinancialStatementBundle(symbol="AAPL")

    assert period.fiscal_quarter is None
    assert period.start_date is None
    assert period.currency is None
    assert income_statement.revenue is None
    assert income_statement.source is None
    assert balance_sheet.total_assets is None
    assert cash_flow_statement.free_cash_flow is None
    assert bundle.income_statement is None
