"""Yahoo Finance-backed financial statement provider."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from importlib import import_module
from math import isfinite
from types import ModuleType
from typing import Any

from parakeetnest.financials.models import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementRequest,
    IncomeStatement,
)
from parakeetnest.financials.provider import (
    FinancialStatementProvider,
    FinancialStatementProviderError,
)


class YahooFinancialStatementProvider(FinancialStatementProvider):
    """Normalize yfinance statement tables into Financial Statement Layer models."""

    _INCOME_FIELDS = {
        "revenue": ("Total Revenue", "Operating Revenue"),
        "cost_of_revenue": ("Cost Of Revenue", "Reconciled Cost Of Revenue"),
        "gross_profit": ("Gross Profit",),
        "operating_income": ("Operating Income",),
        "net_income": ("Net Income", "Net Income Common Stockholders"),
        "eps_basic": ("Basic EPS",),
        "eps_diluted": ("Diluted EPS",),
        "shares_basic": ("Basic Average Shares",),
        "shares_diluted": ("Diluted Average Shares",),
    }
    _BALANCE_FIELDS = {
        "total_assets": ("Total Assets",),
        "total_liabilities": (
            "Total Liabilities Net Minority Interest",
            "Total Liabilities",
        ),
        "total_equity": (
            "Stockholders Equity",
            "Total Equity Gross Minority Interest",
        ),
        "cash_and_equivalents": (
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
        ),
        "short_term_investments": (
            "Other Short Term Investments",
            "Short Term Investments",
        ),
        "total_debt": ("Total Debt",),
        "current_assets": ("Current Assets", "Total Current Assets"),
        "current_liabilities": (
            "Current Liabilities",
            "Total Current Liabilities",
        ),
    }
    _CASH_FLOW_FIELDS = {
        "operating_cash_flow": ("Operating Cash Flow", "Total Cash From Operating Activities"),
        "investing_cash_flow": (
            "Investing Cash Flow",
            "Total Cashflows From Investing Activities",
        ),
        "financing_cash_flow": ("Financing Cash Flow", "Total Cash From Financing Activities"),
        "capital_expenditures": ("Capital Expenditure", "Capital Expenditures"),
        "free_cash_flow": ("Free Cash Flow",),
        "depreciation_and_amortization": (
            "Depreciation And Amortization",
            "Depreciation Amortization Depletion",
        ),
        "stock_based_compensation": ("Stock Based Compensation",),
    }

    def __init__(
        self,
        yfinance_module: ModuleType | Any | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._yf = yfinance_module
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def name(self) -> str:
        return "yahoo"

    def get_income_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[IncomeStatement]:
        ticker = self._ticker(request.symbol)
        table = self._statement_table(ticker, "income", request.period_type)
        retrieved_at = self._retrieved_at()
        return [
            IncomeStatement(
                period=self._period(request, period_end),
                source=self.name,
                retrieved_at=retrieved_at,
                **self._field_values(table, column, self._INCOME_FIELDS),
            )
            for period_end, column in self._period_columns(table, request.limit)
        ]

    def get_balance_sheet(
        self,
        request: FinancialStatementRequest,
    ) -> list[BalanceSheet]:
        ticker = self._ticker(request.symbol)
        table = self._statement_table(ticker, "balance", request.period_type)
        retrieved_at = self._retrieved_at()
        return [
            BalanceSheet(
                period=self._period(request, period_end),
                source=self.name,
                retrieved_at=retrieved_at,
                **self._field_values(table, column, self._BALANCE_FIELDS),
            )
            for period_end, column in self._period_columns(table, request.limit)
        ]

    def get_cash_flow_statement(
        self,
        request: FinancialStatementRequest,
    ) -> list[CashFlowStatement]:
        ticker = self._ticker(request.symbol)
        table = self._statement_table(ticker, "cash_flow", request.period_type)
        retrieved_at = self._retrieved_at()
        return [
            CashFlowStatement(
                period=self._period(request, period_end),
                source=self.name,
                retrieved_at=retrieved_at,
                **self._field_values(table, column, self._CASH_FLOW_FIELDS),
            )
            for period_end, column in self._period_columns(table, request.limit)
        ]

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        ticker = self._ticker(request.symbol)
        retrieved_at = self._retrieved_at()
        tables: dict[str, Any] = {}
        failures: list[str] = []
        for statement_name in ("income", "balance", "cash_flow"):
            try:
                tables[statement_name] = self._statement_table(
                    ticker,
                    statement_name,
                    request.period_type,
                )
            except FinancialStatementProviderError as exc:
                failures.append(f"{statement_name}: {exc}")

        statements_by_period: dict[
            date,
            dict[str, IncomeStatement | BalanceSheet | CashFlowStatement],
        ] = {}
        builders = (
            ("income", IncomeStatement, self._INCOME_FIELDS),
            ("balance", BalanceSheet, self._BALANCE_FIELDS),
            ("cash_flow", CashFlowStatement, self._CASH_FLOW_FIELDS),
        )
        if request.period_type is FinancialPeriodType.TRAILING_TWELVE_MONTHS:
            latest_columns = {
                statement_name: columns[0]
                for statement_name, table in tables.items()
                if (columns := self._period_columns(table, 1))
            }
            if latest_columns:
                period_end = max(value[0] for value in latest_columns.values())
                values: dict[
                    str,
                    IncomeStatement | BalanceSheet | CashFlowStatement,
                ] = {}
                for statement_name, model, field_aliases in builders:
                    column_details = latest_columns.get(statement_name)
                    if column_details is None:
                        continue
                    _, column = column_details
                    values[statement_name] = model(
                        period=self._period(request, period_end),
                        source=self.name,
                        retrieved_at=retrieved_at,
                        **self._field_values(
                            tables[statement_name],
                            column,
                            field_aliases,
                        ),
                    )
                return [
                    FinancialStatementBundle(
                        symbol=request.symbol,
                        income_statement=values.get("income"),
                        balance_sheet=values.get("balance"),
                        cash_flow_statement=values.get("cash_flow"),
                        source=self.name,
                        retrieved_at=retrieved_at,
                    )
                ]

        for statement_name, model, field_aliases in builders:
            table = tables.get(statement_name)
            for period_end, column in self._period_columns(table, request.limit):
                statements_by_period.setdefault(period_end, {})[statement_name] = model(
                    period=self._period(request, period_end),
                    source=self.name,
                    retrieved_at=retrieved_at,
                    **self._field_values(table, column, field_aliases),
                )

        if not statements_by_period and failures:
            raise FinancialStatementProviderError(
                f"Yahoo Finance statements failed for {request.symbol}: "
                + "; ".join(failures)
            )

        return [
            FinancialStatementBundle(
                symbol=request.symbol,
                income_statement=values.get("income"),
                balance_sheet=values.get("balance"),
                cash_flow_statement=values.get("cash_flow"),
                source=self.name,
                retrieved_at=retrieved_at,
            )
            for _, values in sorted(
                statements_by_period.items(),
                key=lambda item: item[0],
                reverse=True,
            )[: request.limit]
        ]

    def _statement_table(
        self,
        ticker: Any,
        statement_name: str,
        period_type: FinancialPeriodType,
    ) -> Any:
        try:
            if period_type is FinancialPeriodType.TRAILING_TWELVE_MONTHS:
                attribute = {
                    "income": "ttm_income_stmt",
                    "balance": "quarterly_balance_sheet",
                    "cash_flow": "ttm_cash_flow",
                }[statement_name]
                return getattr(ticker, attribute, None)

            frequency = (
                "yearly"
                if period_type is FinancialPeriodType.ANNUAL
                else "quarterly"
            )
            method_name = {
                "income": "get_income_stmt",
                "balance": "get_balance_sheet",
                "cash_flow": "get_cash_flow",
            }[statement_name]
            return getattr(ticker, method_name)(freq=frequency)
        except Exception as exc:
            raise FinancialStatementProviderError(
                f"Yahoo Finance {statement_name} request failed"
            ) from exc

    def _ticker(self, symbol: str) -> Any:
        try:
            return self._yfinance().Ticker(symbol)
        except Exception as exc:
            raise FinancialStatementProviderError(
                f"Yahoo Finance could not initialize ticker {symbol}"
            ) from exc

    def _yfinance(self) -> Any:
        if self._yf is None:
            self._yf = import_module("yfinance")
        return self._yf

    def _period_columns(self, table: Any, limit: int) -> list[tuple[date, Any]]:
        if table is None:
            return []
        columns = getattr(table, "columns", ())
        parsed = [
            (period_end, column)
            for column in columns
            if (period_end := self._date_value(column)) is not None
        ]
        parsed.sort(key=lambda item: item[0], reverse=True)
        return parsed[:limit]

    def _field_values(
        self,
        table: Any,
        column: Any,
        field_aliases: Mapping[str, tuple[str, ...]],
    ) -> dict[str, float | None]:
        return {
            field_name: self._first_value(table, column, aliases)
            for field_name, aliases in field_aliases.items()
        }

    def _first_value(
        self,
        table: Any,
        column: Any,
        aliases: tuple[str, ...],
    ) -> float | None:
        normalized_rows = {
            self._normalize_label(row_name): row_name
            for row_name in getattr(table, "index", ())
        }
        for row_name in aliases:
            actual_row_name = normalized_rows.get(self._normalize_label(row_name))
            if actual_row_name is None:
                continue
            try:
                raw_value = table.at[actual_row_name, column]
            except (AttributeError, KeyError, TypeError):
                try:
                    raw_value = table.loc[actual_row_name, column]
                except (AttributeError, KeyError, TypeError):
                    continue
            value = self._optional_float(raw_value)
            if value is not None:
                return value
        return None

    @staticmethod
    def _normalize_label(value: Any) -> str:
        return "".join(
            character
            for character in str(value).casefold()
            if character.isalnum()
        )

    def _period(
        self,
        request: FinancialStatementRequest,
        period_end: date,
    ) -> FinancialStatementPeriod:
        fiscal_quarter = None
        if request.period_type is FinancialPeriodType.QUARTERLY:
            fiscal_quarter = (period_end.month - 1) // 3 + 1
        return FinancialStatementPeriod(
            symbol=request.symbol,
            period_type=request.period_type,
            fiscal_year=period_end.year,
            fiscal_quarter=fiscal_quarter,
            end_date=period_end,
            report_date=period_end,
        )

    @staticmethod
    def _date_value(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        to_datetime = getattr(value, "to_pydatetime", None)
        if callable(to_datetime):
            parsed = to_datetime()
            return parsed.date() if isinstance(parsed, datetime) else None
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if isfinite(parsed) else None

    def _retrieved_at(self) -> datetime:
        retrieved_at = self._clock()
        if retrieved_at.tzinfo is None:
            return retrieved_at.replace(tzinfo=UTC)
        return retrieved_at


__all__ = ["YahooFinancialStatementProvider"]
