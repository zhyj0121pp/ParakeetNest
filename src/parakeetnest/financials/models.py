"""Provider-agnostic Financial Statement Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class FinancialPeriodType(str, Enum):
    """Supported provider-independent financial statement period types."""

    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TRAILING_TWELVE_MONTHS = "ttm"


@dataclass(frozen=True)
class FinancialStatementPeriod:
    """Normalized fiscal period metadata for a financial statement."""

    symbol: str
    period_type: FinancialPeriodType
    fiscal_year: int
    fiscal_quarter: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    report_date: date | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        """Normalize stable identity fields and validate period type values."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if not isinstance(self.period_type, FinancialPeriodType):
            object.__setattr__(
                self,
                "period_type",
                FinancialPeriodType(self.period_type),
            )
        if self.currency is not None:
            object.__setattr__(self, "currency", self.currency.strip().upper())


@dataclass(frozen=True)
class IncomeStatement:
    """Common income statement line items for one fiscal period."""

    period: FinancialStatementPeriod
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps_basic: float | None = None
    eps_diluted: float | None = None
    shares_basic: float | None = None
    shares_diluted: float | None = None
    source: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class BalanceSheet:
    """Common balance sheet line items for one fiscal period."""

    period: FinancialStatementPeriod
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    cash_and_equivalents: float | None = None
    short_term_investments: float | None = None
    total_debt: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    source: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class CashFlowStatement:
    """Common cash flow statement line items for one fiscal period."""

    period: FinancialStatementPeriod
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None
    capital_expenditures: float | None = None
    free_cash_flow: float | None = None
    depreciation_and_amortization: float | None = None
    stock_based_compensation: float | None = None
    source: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True)
class FinancialStatementBundle:
    """Grouped financial statements for one symbol and fiscal period."""

    symbol: str
    income_statement: IncomeStatement | None = None
    balance_sheet: BalanceSheet | None = None
    cash_flow_statement: CashFlowStatement | None = None
    source: str | None = None
    retrieved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize symbol identity for stable comparisons."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())


@dataclass(frozen=True)
class FinancialStatementRequest:
    """Provider-neutral financial statement request."""

    symbol: str
    period_type: FinancialPeriodType
    limit: int = 4

    def __post_init__(self) -> None:
        """Normalize request fields used by providers."""
        if self.limit < 1:
            raise ValueError("limit must be at least 1")

        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if not isinstance(self.period_type, FinancialPeriodType):
            object.__setattr__(
                self,
                "period_type",
                FinancialPeriodType(self.period_type),
            )


__all__ = [
    "BalanceSheet",
    "CashFlowStatement",
    "FinancialPeriodType",
    "FinancialStatementBundle",
    "FinancialStatementPeriod",
    "FinancialStatementRequest",
    "IncomeStatement",
]
