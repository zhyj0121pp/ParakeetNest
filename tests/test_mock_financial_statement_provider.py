"""Tests for the deterministic mock financial statement provider."""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime

from parakeetnest.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementProvider,
    FinancialStatementRequest,
    IncomeStatement,
    MockFinancialStatementProvider,
)


def test_mock_provider_name() -> None:
    """The mock provider should expose a stable provider name."""
    provider = MockFinancialStatementProvider()

    assert provider.name == "mock"


def test_mock_provider_returns_deterministic_statements() -> None:
    """Repeated calls and provider instances should return identical data."""
    first_provider = MockFinancialStatementProvider()
    second_provider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="AAPL",
        period_type=FinancialPeriodType.ANNUAL,
        limit=2,
    )

    first_income_statements = first_provider.get_income_statement(request)
    second_income_statements = second_provider.get_income_statement(request)
    first_balance_sheets = first_provider.get_balance_sheet(request)
    second_balance_sheets = second_provider.get_balance_sheet(request)
    first_cash_flow_statements = first_provider.get_cash_flow_statement(request)
    second_cash_flow_statements = second_provider.get_cash_flow_statement(request)

    assert first_income_statements == second_income_statements
    assert first_balance_sheets == second_balance_sheets
    assert first_cash_flow_statements == second_cash_flow_statements
    assert all(isinstance(statement, IncomeStatement) for statement in first_income_statements)
    assert all(isinstance(statement, BalanceSheet) for statement in first_balance_sheets)
    assert all(
        isinstance(statement, CashFlowStatement)
        for statement in first_cash_flow_statements
    )
    assert first_income_statements[0].source == "mock"
    assert first_income_statements[0].retrieved_at == datetime(
        2026,
        6,
        29,
        12,
        0,
        tzinfo=UTC,
    )


def test_mock_provider_uses_request_normalization() -> None:
    """The provider should honor normalized request symbol and period fields."""
    provider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol=" nvda ",
        period_type="quarterly",
        limit=1,
    )

    statement = provider.get_income_statement(request)[0]

    assert statement.period.symbol == "NVDA"
    assert statement.period.period_type is FinancialPeriodType.QUARTERLY
    assert statement.period.fiscal_year == 2026
    assert statement.period.fiscal_quarter == 2
    assert statement.period.start_date == date(2026, 4, 1)
    assert statement.period.end_date == date(2026, 6, 28)
    assert statement.period.currency == "USD"


def test_mock_provider_limit_controls_number_of_results() -> None:
    """The mock provider should honor the provider-neutral request limit."""
    provider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="MSFT",
        period_type=FinancialPeriodType.QUARTERLY,
        limit=3,
    )

    income_statements = provider.get_income_statement(request)
    balance_sheets = provider.get_balance_sheet(request)
    cash_flow_statements = provider.get_cash_flow_statement(request)

    assert len(income_statements) == 3
    assert len(balance_sheets) == 3
    assert len(cash_flow_statements) == 3
    assert [statement.period.fiscal_quarter for statement in income_statements] == [
        2,
        1,
        4,
    ]


def test_mock_provider_bundle_contains_all_statement_types() -> None:
    """Bundles should group income, balance sheet, and cash flow statements."""
    provider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="TSLA",
        period_type=FinancialPeriodType.ANNUAL,
        limit=2,
    )

    bundles = provider.get_financial_statement_bundle(request)

    assert len(bundles) == 2
    assert bundles[0].symbol == "TSLA"
    assert isinstance(bundles[0].income_statement, IncomeStatement)
    assert isinstance(bundles[0].balance_sheet, BalanceSheet)
    assert isinstance(bundles[0].cash_flow_statement, CashFlowStatement)
    assert bundles[0].source == "mock"


def test_mock_provider_bundle_statements_share_the_same_period() -> None:
    """All statements in each bundle should align to one fiscal period."""
    provider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="AAPL",
        period_type=FinancialPeriodType.TRAILING_TWELVE_MONTHS,
        limit=3,
    )

    bundles = provider.get_financial_statement_bundle(request)

    for bundle in bundles:
        assert bundle.income_statement is not None
        assert bundle.balance_sheet is not None
        assert bundle.cash_flow_statement is not None
        period = bundle.income_statement.period
        assert bundle.balance_sheet.period == period
        assert bundle.cash_flow_statement.period == period
        assert period.period_type is FinancialPeriodType.TRAILING_TWELVE_MONTHS


def test_mock_provider_repeated_bundle_calls_return_identical_results() -> None:
    """Repeated bundle calls should return equal deterministic results."""
    provider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="AMD",
        period_type=FinancialPeriodType.ANNUAL,
        limit=4,
    )

    assert provider.get_financial_statement_bundle(
        request,
    ) == provider.get_financial_statement_bundle(request)


def test_mock_provider_does_not_import_external_clients() -> None:
    """Using the mock provider should not import API or HTTP client modules."""
    forbidden_modules = {"aiohttp", "httpx", "requests", "yfinance"}

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: FinancialStatementProvider = MockFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="AAPL",
        period_type=FinancialPeriodType.ANNUAL,
    )

    assert provider.get_income_statement(request)[0].period.symbol == "AAPL"
    assert forbidden_modules.isdisjoint(sys.modules)
