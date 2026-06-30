"""Deterministic in-memory financial statement provider."""

from __future__ import annotations

from datetime import UTC, date, datetime

from parakeetnest.financials.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementRequest,
    IncomeStatement,
)
from parakeetnest.financials.provider import FinancialStatementProvider


class MockFinancialStatementProvider(FinancialStatementProvider):
    """Financial statement provider backed by deterministic generated fixtures."""

    _RETRIEVED_AT = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    _LATEST_YEAR = 2026
    _LATEST_QUARTER = 2

    @property
    def name(self) -> str:
        """Return the stable provider name used for provenance."""
        return "mock"

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        """Return deterministic income statements for the request."""
        return [
            IncomeStatement(
                period=period,
                revenue=self._amount(request.symbol, index, 100_000_000_000.0),
                cost_of_revenue=self._amount(
                    request.symbol,
                    index,
                    42_000_000_000.0,
                ),
                gross_profit=self._amount(request.symbol, index, 58_000_000_000.0),
                operating_income=self._amount(
                    request.symbol,
                    index,
                    31_000_000_000.0,
                ),
                net_income=self._amount(request.symbol, index, 24_000_000_000.0),
                eps_basic=round(
                    3.40 + self._symbol_factor(request.symbol) / 100 + index * 0.12,
                    2,
                ),
                eps_diluted=round(
                    3.35 + self._symbol_factor(request.symbol) / 100 + index * 0.11,
                    2,
                ),
                shares_basic=self._amount(request.symbol, index, 7_000_000_000.0),
                shares_diluted=self._amount(request.symbol, index, 7_200_000_000.0),
                source=self.name,
                retrieved_at=self._RETRIEVED_AT,
            )
            for index, period in enumerate(self._periods(request))
        ]

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        """Return deterministic balance sheets for the request."""
        return [
            BalanceSheet(
                period=period,
                total_assets=self._amount(request.symbol, index, 280_000_000_000.0),
                total_liabilities=self._amount(
                    request.symbol,
                    index,
                    145_000_000_000.0,
                ),
                total_equity=self._amount(request.symbol, index, 135_000_000_000.0),
                cash_and_equivalents=self._amount(
                    request.symbol,
                    index,
                    35_000_000_000.0,
                ),
                short_term_investments=self._amount(
                    request.symbol,
                    index,
                    18_000_000_000.0,
                ),
                total_debt=self._amount(request.symbol, index, 48_000_000_000.0),
                current_assets=self._amount(request.symbol, index, 92_000_000_000.0),
                current_liabilities=self._amount(
                    request.symbol,
                    index,
                    61_000_000_000.0,
                ),
                source=self.name,
                retrieved_at=self._RETRIEVED_AT,
            )
            for index, period in enumerate(self._periods(request))
        ]

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        """Return deterministic cash flow statements for the request."""
        return [
            CashFlowStatement(
                period=period,
                operating_cash_flow=self._amount(
                    request.symbol,
                    index,
                    36_000_000_000.0,
                ),
                investing_cash_flow=-self._amount(
                    request.symbol,
                    index,
                    12_000_000_000.0,
                ),
                financing_cash_flow=-self._amount(
                    request.symbol,
                    index,
                    9_000_000_000.0,
                ),
                capital_expenditures=-self._amount(
                    request.symbol,
                    index,
                    7_000_000_000.0,
                ),
                free_cash_flow=self._amount(request.symbol, index, 29_000_000_000.0),
                depreciation_and_amortization=self._amount(
                    request.symbol,
                    index,
                    6_000_000_000.0,
                ),
                stock_based_compensation=self._amount(
                    request.symbol,
                    index,
                    3_000_000_000.0,
                ),
                source=self.name,
                retrieved_at=self._RETRIEVED_AT,
            )
            for index, period in enumerate(self._periods(request))
        ]

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        """Return deterministic bundles by reusing individual statement methods."""
        income_statements = self.get_income_statement(request)
        balance_sheets = self.get_balance_sheet(request)
        cash_flow_statements = self.get_cash_flow_statement(request)

        return [
            FinancialStatementBundle(
                symbol=request.symbol,
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow_statement=cash_flow_statement,
                source=self.name,
                retrieved_at=self._RETRIEVED_AT,
            )
            for income_statement, balance_sheet, cash_flow_statement in zip(
                income_statements,
                balance_sheets,
                cash_flow_statements,
                strict=True,
            )
        ]

    def _periods(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementPeriod]:
        return [
            self._period(request.symbol, request.period_type, index)
            for index in range(request.limit)
        ]

    def _period(
        self,
        symbol: str,
        period_type: FinancialPeriodType,
        index: int,
    ) -> FinancialStatementPeriod:
        if period_type is FinancialPeriodType.QUARTERLY:
            fiscal_year, fiscal_quarter = self._quarter_for_index(index)
            start_month = (fiscal_quarter - 1) * 3 + 1
            end_month = start_month + 2
            return FinancialStatementPeriod(
                symbol=symbol,
                period_type=period_type,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                start_date=date(fiscal_year, start_month, 1),
                end_date=date(fiscal_year, end_month, 28),
                report_date=date(fiscal_year, end_month, 28),
                currency="USD",
            )

        fiscal_year = self._LATEST_YEAR - index
        return FinancialStatementPeriod(
            symbol=symbol,
            period_type=period_type,
            fiscal_year=fiscal_year,
            start_date=date(fiscal_year, 1, 1),
            end_date=date(fiscal_year, 12, 31),
            report_date=date(fiscal_year, 12, 31),
            currency="USD",
        )

    def _quarter_for_index(self, index: int) -> tuple[int, int]:
        zero_based_quarter = self._LATEST_QUARTER - 1 - index
        fiscal_year = self._LATEST_YEAR + zero_based_quarter // 4
        fiscal_quarter = zero_based_quarter % 4 + 1
        return fiscal_year, fiscal_quarter

    def _amount(self, symbol: str, index: int, base: float) -> float:
        multiplier = 1 + self._symbol_factor(symbol) / 100
        period_decay = 1 - index * 0.04
        return round(base * multiplier * period_decay, 2)

    def _symbol_factor(self, symbol: str) -> int:
        return sum(ord(character) for character in symbol) % 17


__all__ = ["MockFinancialStatementProvider"]
