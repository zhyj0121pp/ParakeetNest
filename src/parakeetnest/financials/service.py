"""Provider-agnostic financial statement service boundary."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from parakeetnest.financials.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatementBundle,
    FinancialStatementRequest,
    IncomeStatement,
)
from parakeetnest.financials.provider import (
    FinancialStatementProvider,
    FinancialStatementProviderError,
)
from parakeetnest.financials.registry import FinancialStatementProviderRegistry

_T = TypeVar("_T")


class FinancialStatementService:
    """Single entry point for provider-backed financial statement requests."""

    def __init__(
        self,
        provider: FinancialStatementProvider | FinancialStatementProviderRegistry,
    ) -> None:
        """Initialize the service with a provider or provider registry."""
        self._provider_source = provider

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Return provider-backed income statements for the request."""
        provider = self._get_provider()
        return self._call_provider(provider.get_income_statement, request)

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Return provider-backed balance sheets for the request."""
        provider = self._get_provider()
        return self._call_provider(provider.get_balance_sheet, request)

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Return provider-backed cash flow statements for the request."""
        provider = self._get_provider()
        return self._call_provider(provider.get_cash_flow_statement, request)

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Return provider-backed financial statement bundles for the request."""
        provider = self._get_provider()
        return self._call_provider(
            provider.get_financial_statement_bundle,
            request,
        )

    def _get_provider(self) -> FinancialStatementProvider:
        if isinstance(self._provider_source, FinancialStatementProviderRegistry):
            return self._provider_source.get_default_provider()
        return self._provider_source

    def _call_provider(
        self,
        method: Callable[[FinancialStatementRequest], _T],
        request: FinancialStatementRequest,
    ) -> _T:
        try:
            return method(request)
        except FinancialStatementProviderError:
            raise
        except Exception as exc:
            raise FinancialStatementProviderError(str(exc)) from exc


__all__ = ["FinancialStatementService"]
