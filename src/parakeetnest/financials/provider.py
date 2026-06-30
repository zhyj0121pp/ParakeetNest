"""Provider contract for financial statement integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from parakeetnest.financials.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatementBundle,
    FinancialStatementRequest,
    IncomeStatement,
)


class FinancialStatementProviderError(Exception):
    """Base class for provider-independent financial statement failures."""


class FinancialStatementProvider(ABC):
    """Abstract contract for provider-neutral financial statement data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable provider name used for diagnostics and provenance."""

    @abstractmethod
    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Return provider-neutral income statements for the request."""

    @abstractmethod
    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Return provider-neutral balance sheets for the request."""

    @abstractmethod
    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Return provider-neutral cash flow statements for the request."""

    @abstractmethod
    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Return grouped provider-neutral statements for the request."""


__all__ = [
    "FinancialStatementProvider",
    "FinancialStatementProviderError",
]
