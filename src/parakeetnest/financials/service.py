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

_T = TypeVar("_T")


class FinancialStatementService:
    """Single entry point for provider-backed financial statement requests."""

    def __init__(self, provider: FinancialStatementProvider) -> None:
        """Initialize the service with one financial statement provider."""
        self._provider = provider

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Return provider-backed income statements for the request."""
        return self._call_provider(self._provider.get_income_statement, request)

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Return provider-backed balance sheets for the request."""
        return self._call_provider(self._provider.get_balance_sheet, request)

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Return provider-backed cash flow statements for the request."""
        return self._call_provider(self._provider.get_cash_flow_statement, request)

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Return provider-backed financial statement bundles for the request."""
        return self._call_provider(
            self._provider.get_financial_statement_bundle,
            request,
        )

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
