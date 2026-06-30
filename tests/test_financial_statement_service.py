"""Tests for the provider-agnostic financial statement service."""

from __future__ import annotations

from datetime import UTC, date, datetime

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
    FinancialStatementService,
    IncomeStatement,
    MockFinancialStatementProvider,
)


class ProviderSpecificFinancialError(Exception):
    """Provider-specific failure that should not leak through the service."""


class SpyFinancialStatementProvider:
    """Provider test double that records financial statement service delegation."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.income_calls: list[FinancialStatementRequest] = []
        self.balance_calls: list[FinancialStatementRequest] = []
        self.cash_flow_calls: list[FinancialStatementRequest] = []
        self.bundle_calls: list[FinancialStatementRequest] = []
        self.period = FinancialStatementPeriod(
            symbol="AMD",
            period_type=FinancialPeriodType.ANNUAL,
            fiscal_year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            currency="USD",
        )
        self.income_statements = [
            IncomeStatement(
                period=self.period,
                revenue=100.0,
                net_income=25.0,
                source="spy",
                retrieved_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
            )
        ]
        self.balance_sheets = [
            BalanceSheet(
                period=self.period,
                total_assets=300.0,
                total_liabilities=125.0,
                total_equity=175.0,
                source="spy",
            )
        ]
        self.cash_flow_statements = [
            CashFlowStatement(
                period=self.period,
                operating_cash_flow=40.0,
                free_cash_flow=30.0,
                source="spy",
            )
        ]
        self.bundles = [
            FinancialStatementBundle(
                symbol="AMD",
                income_statement=self.income_statements[0],
                balance_sheet=self.balance_sheets[0],
                cash_flow_statement=self.cash_flow_statements[0],
                source="spy",
            )
        ]

    @property
    def name(self) -> str:
        """Return a stable provider name for provenance."""
        return "spy"

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Record and return provider-backed income statements."""
        self.income_calls.append(request)
        self._raise_if_configured()
        return self.income_statements

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Record and return provider-backed balance sheets."""
        self.balance_calls.append(request)
        self._raise_if_configured()
        return self.balance_sheets

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Record and return provider-backed cash flow statements."""
        self.cash_flow_calls.append(request)
        self._raise_if_configured()
        return self.cash_flow_statements

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Record and return provider-backed financial statement bundles."""
        self.bundle_calls.append(request)
        self._raise_if_configured()
        return self.bundles

    def _raise_if_configured(self) -> None:
        if self.error is not None:
            raise self.error


def test_get_income_statement_delegates_to_provider_once() -> None:
    provider = SpyFinancialStatementProvider()
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    income_statements = service.get_income_statement(request)

    assert income_statements is provider.income_statements
    assert provider.income_calls == [request]


def test_get_balance_sheet_delegates_to_provider_once() -> None:
    provider = SpyFinancialStatementProvider()
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    balance_sheets = service.get_balance_sheet(request)

    assert balance_sheets is provider.balance_sheets
    assert provider.balance_calls == [request]


def test_get_cash_flow_statement_delegates_to_provider_once() -> None:
    provider = SpyFinancialStatementProvider()
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    cash_flow_statements = service.get_cash_flow_statement(request)

    assert cash_flow_statements is provider.cash_flow_statements
    assert provider.cash_flow_calls == [request]


def test_get_financial_statement_bundle_delegates_to_provider_once() -> None:
    provider = SpyFinancialStatementProvider()
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    bundles = service.get_financial_statement_bundle(request)

    assert bundles is provider.bundles
    assert provider.bundle_calls == [request]


def test_service_does_not_modify_provider_results() -> None:
    provider = SpyFinancialStatementProvider()
    service = FinancialStatementService(provider)
    expected_income_statements = list(provider.income_statements)
    expected_balance_sheets = list(provider.balance_sheets)
    expected_cash_flow_statements = list(provider.cash_flow_statements)
    expected_bundles = list(provider.bundles)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    assert service.get_income_statement(request) is provider.income_statements
    assert service.get_balance_sheet(request) is provider.balance_sheets
    assert service.get_cash_flow_statement(request) is provider.cash_flow_statements
    assert service.get_financial_statement_bundle(request) is provider.bundles
    assert provider.income_statements == expected_income_statements
    assert provider.balance_sheets == expected_balance_sheets
    assert provider.cash_flow_statements == expected_cash_flow_statements
    assert provider.bundles == expected_bundles


def test_provider_specific_errors_are_wrapped() -> None:
    provider = SpyFinancialStatementProvider(
        error=ProviderSpecificFinancialError("provider unavailable")
    )
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    with pytest.raises(FinancialStatementProviderError) as exc_info:
        service.get_income_statement(request)

    assert str(exc_info.value) == "provider unavailable"
    assert isinstance(exc_info.value.__cause__, ProviderSpecificFinancialError)


def test_provider_neutral_errors_propagate_unchanged() -> None:
    error = FinancialStatementProviderError("financial statements unavailable")
    provider = SpyFinancialStatementProvider(error=error)
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    with pytest.raises(FinancialStatementProviderError) as exc_info:
        service.get_balance_sheet(request)

    assert exc_info.value is error


def test_service_works_with_mock_financial_statement_provider() -> None:
    provider: FinancialStatementProvider = MockFinancialStatementProvider()
    service = FinancialStatementService(provider)
    request = FinancialStatementRequest(
        symbol="aapl",
        period_type=FinancialPeriodType.QUARTERLY,
        limit=2,
    )

    income_statements = service.get_income_statement(request)
    balance_sheets = service.get_balance_sheet(request)
    cash_flow_statements = service.get_cash_flow_statement(request)
    bundles = service.get_financial_statement_bundle(request)

    assert len(income_statements) == 2
    assert len(balance_sheets) == 2
    assert len(cash_flow_statements) == 2
    assert len(bundles) == 2
    assert income_statements[0].period.symbol == "AAPL"
    assert bundles[0].income_statement == income_statements[0]
