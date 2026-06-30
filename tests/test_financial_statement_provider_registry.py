"""Tests for financial statement provider registration and defaults."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from parakeetnest.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementProviderRegistry,
    FinancialStatementRequest,
    FinancialStatementService,
    IncomeStatement,
)


class RecordingFinancialStatementProvider:
    """Financial statement provider test double for registry lookups."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        self.income_calls: list[FinancialStatementRequest] = []
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
                source=self.provider_name,
                retrieved_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
            )
        ]

    @property
    def name(self) -> str:
        """Return a stable provider name."""
        return self.provider_name

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Record and return provider-backed income statements."""
        self.income_calls.append(request)
        return self.income_statements

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Registry tests do not exercise balance sheet lookup."""
        return []

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Registry tests do not exercise cash flow lookup."""
        return []

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Registry tests do not exercise bundle lookup."""
        return []


def test_registry_registers_provider() -> None:
    registry = FinancialStatementProviderRegistry()
    provider = RecordingFinancialStatementProvider("recording")

    registry.register_provider(provider)

    assert registry.list_providers() == (provider,)


def test_registry_unregisters_provider() -> None:
    provider = RecordingFinancialStatementProvider("recording")
    registry = FinancialStatementProviderRegistry([provider])

    registry.unregister_provider("recording")

    assert registry.list_providers() == ()
    with pytest.raises(KeyError, match="Unknown financial statement provider"):
        registry.get_provider("recording")


def test_registry_rejects_duplicate_registration() -> None:
    registry = FinancialStatementProviderRegistry()
    registry.register_provider(RecordingFinancialStatementProvider("mock"))

    with pytest.raises(
        ValueError,
        match="Financial statement provider already registered: mock",
    ):
        registry.register_provider(RecordingFinancialStatementProvider("MOCK"))


def test_registry_gets_provider() -> None:
    registry = FinancialStatementProviderRegistry()
    provider = RecordingFinancialStatementProvider("recording")

    registry.register_provider(provider)

    assert registry.get_provider("recording") is provider
    assert registry.get_provider(" RECORDING ") is provider


def test_registry_unknown_provider_lookup_raises_key_error() -> None:
    registry = FinancialStatementProviderRegistry()

    with pytest.raises(KeyError, match="Unknown financial statement provider: missing"):
        registry.get_provider("missing")


def test_registry_sets_and_gets_default_provider() -> None:
    first_provider = RecordingFinancialStatementProvider("first")
    second_provider = RecordingFinancialStatementProvider("second")
    registry = FinancialStatementProviderRegistry([first_provider, second_provider])

    registry.set_default_provider("second")

    assert registry.get_default_provider() is second_provider


def test_registry_rejects_unknown_default_provider() -> None:
    registry = FinancialStatementProviderRegistry()

    with pytest.raises(KeyError, match="Unknown financial statement provider: missing"):
        registry.set_default_provider("missing")


def test_registry_switches_default_provider() -> None:
    first_provider = RecordingFinancialStatementProvider("first")
    second_provider = RecordingFinancialStatementProvider("second")
    registry = FinancialStatementProviderRegistry(
        [first_provider, second_provider],
        default_provider="first",
    )

    registry.set_default_provider("second")

    assert registry.get_default_provider() is second_provider


def test_constructor_initializes_providers_and_single_provider_default() -> None:
    provider = RecordingFinancialStatementProvider("single")
    registry = FinancialStatementProviderRegistry([provider])

    assert registry.list_providers() == (provider,)
    assert registry.get_default_provider() is provider


def test_constructor_initializes_explicit_default_provider() -> None:
    first_provider = RecordingFinancialStatementProvider("first")
    second_provider = RecordingFinancialStatementProvider("second")
    registry = FinancialStatementProviderRegistry(
        providers=[first_provider, second_provider],
        default_provider="second",
    )

    assert registry.get_default_provider() is second_provider


def test_service_works_with_registry() -> None:
    provider = RecordingFinancialStatementProvider("recording")
    registry = FinancialStatementProviderRegistry([provider])
    service = FinancialStatementService(registry)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    income_statements = service.get_income_statement(request)

    assert income_statements is provider.income_statements
    assert provider.income_calls == [request]


def test_changing_default_provider_immediately_affects_service_behavior() -> None:
    first_provider = RecordingFinancialStatementProvider("first")
    second_provider = RecordingFinancialStatementProvider("second")
    registry = FinancialStatementProviderRegistry(
        [first_provider, second_provider],
        default_provider="first",
    )
    service = FinancialStatementService(registry)
    request = FinancialStatementRequest(
        symbol="amd",
        period_type=FinancialPeriodType.ANNUAL,
    )

    first_income_statements = service.get_income_statement(request)
    registry.set_default_provider("second")
    second_income_statements = service.get_income_statement(request)

    assert first_income_statements is first_provider.income_statements
    assert second_income_statements is second_provider.income_statements
    assert first_provider.income_calls == [request]
    assert second_provider.income_calls == [request]
