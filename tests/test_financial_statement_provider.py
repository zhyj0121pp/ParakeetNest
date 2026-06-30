"""Tests for the Financial Statement Provider abstraction."""

from __future__ import annotations

import sys
from datetime import date

import pytest

from parakeetnest.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementProvider,
    FinancialStatementProviderError,
    FinancialStatementRequest,
    IncomeStatement,
)


class FakeFinancialStatementProvider(FinancialStatementProvider):
    """In-memory provider used to verify the provider abstraction contract."""

    @property
    def name(self) -> str:
        """Return a stable provider name for provenance."""
        return "fake"

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Return deterministic income statements without external dependencies."""
        return [
            IncomeStatement(
                period=self._period(request),
                revenue=100.0,
                net_income=25.0,
                source=self.name,
            )
        ]

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Return deterministic balance sheets without external dependencies."""
        return [
            BalanceSheet(
                period=self._period(request),
                total_assets=300.0,
                total_liabilities=125.0,
                total_equity=175.0,
                source=self.name,
            )
        ]

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Return deterministic cash flow statements without external dependencies."""
        return [
            CashFlowStatement(
                period=self._period(request),
                operating_cash_flow=40.0,
                free_cash_flow=30.0,
                source=self.name,
            )
        ]

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Return deterministic statement bundles without external dependencies."""
        return [
            FinancialStatementBundle(
                symbol=request.symbol,
                income_statement=self.get_income_statement(request)[0],
                balance_sheet=self.get_balance_sheet(request)[0],
                cash_flow_statement=self.get_cash_flow_statement(request)[0],
                source=self.name,
            )
        ]

    def _period(
        self,
        request: FinancialStatementRequest,
    ) -> FinancialStatementPeriod:
        return FinancialStatementPeriod(
            symbol=request.symbol,
            period_type=request.period_type,
            fiscal_year=2026,
            fiscal_quarter=2,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            currency="USD",
        )


def test_financial_statement_provider_cannot_be_instantiated_directly() -> None:
    """The base provider should require concrete implementations."""
    with pytest.raises(TypeError, match="abstract"):
        FinancialStatementProvider()


def test_concrete_provider_implements_all_abstract_methods() -> None:
    """A complete provider should be instantiable through the abstraction."""
    provider: FinancialStatementProvider = FakeFinancialStatementProvider()

    assert provider.name == "fake"


def test_provider_methods_return_statement_lists() -> None:
    """Provider APIs should return provider-neutral financial statement models."""
    provider: FinancialStatementProvider = FakeFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="aapl",
        period_type=FinancialPeriodType.QUARTERLY,
        limit=1,
    )

    income_statements = provider.get_income_statement(request)
    balance_sheets = provider.get_balance_sheet(request)
    cash_flow_statements = provider.get_cash_flow_statement(request)
    bundles = provider.get_financial_statement_bundle(request)

    assert isinstance(income_statements, list)
    assert isinstance(income_statements[0], IncomeStatement)
    assert income_statements[0].period.symbol == "AAPL"
    assert isinstance(balance_sheets, list)
    assert isinstance(balance_sheets[0], BalanceSheet)
    assert isinstance(cash_flow_statements, list)
    assert isinstance(cash_flow_statements[0], CashFlowStatement)
    assert isinstance(bundles, list)
    assert isinstance(bundles[0], FinancialStatementBundle)
    assert bundles[0].symbol == "AAPL"


def test_provider_error_can_be_raised_and_caught() -> None:
    """Provider failures should use the provider-neutral error type."""
    with pytest.raises(FinancialStatementProviderError, match="unavailable"):
        raise FinancialStatementProviderError("financial statements unavailable")


def test_provider_abstraction_does_not_require_external_data_clients() -> None:
    """Importing and using the abstraction should not import concrete clients."""
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp"}

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = FakeFinancialStatementProvider()
    request = FinancialStatementRequest(
        symbol="AAPL",
        period_type=FinancialPeriodType.ANNUAL,
    )

    assert isinstance(provider.get_income_statement(request)[0], IncomeStatement)
    assert forbidden_modules.isdisjoint(sys.modules)
