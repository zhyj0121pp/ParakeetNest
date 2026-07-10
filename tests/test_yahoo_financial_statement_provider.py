"""Tests for Yahoo-backed financial statement normalization."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from parakeetnest.financials import (
    FinancialPeriodType,
    FinancialStatementProvider,
    FinancialStatementProviderError,
    FinancialStatementRequest,
    YahooFinancialStatementProvider,
)


RETRIEVED_AT = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


class FakeAccessor:
    def __init__(self, values: dict[tuple[str, date], Any]) -> None:
        self._values = values

    def __getitem__(self, key: tuple[str, date]) -> Any:
        return self._values[key]


class FakeTable:
    def __init__(self, values: dict[tuple[str, date], Any]) -> None:
        self._values = values
        self.index = tuple(dict.fromkeys(row for row, _ in values))
        self.columns = tuple(dict.fromkeys(column for _, column in values))
        self.at = FakeAccessor(values)
        self.loc = FakeAccessor(values)


def _table(period: date, **values: float | None) -> FakeTable:
    return FakeTable({(name, period): value for name, value in values.items()})


class FakeTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.calls: list[tuple[str, str]] = []
        annual_period = date(2025, 12, 31)
        quarterly_period = date(2026, 6, 30)
        self.annual_income = _table(
            annual_period,
            **{
                "Total Revenue": 410_000_000_000,
                "Gross Profit": 190_000_000_000,
                "Operating Income": 130_000_000_000,
                "Net Income": 105_000_000_000,
                "Diluted EPS": 6.42,
                "Diluted Average Shares": 15_200_000_000,
            },
        )
        self.annual_balance = _table(
            annual_period,
            **{
                "Total Assets": 365_000_000_000,
                "Total Liabilities Net Minority Interest": 280_000_000_000,
                "Stockholders Equity": 85_000_000_000,
                "Cash And Cash Equivalents": 32_000_000_000,
                "Total Debt": 101_000_000_000,
            },
        )
        self.annual_cash_flow = _table(
            annual_period,
            **{
                "Operating Cash Flow": 118_000_000_000,
                "Capital Expenditure": -12_000_000_000,
                "Free Cash Flow": 106_000_000_000,
                "Stock Based Compensation": 11_000_000_000,
            },
        )
        self.quarterly_income = _table(
            quarterly_period,
            **{"Total Revenue": 102_000_000_000, "Net Income": 25_000_000_000},
        )
        self.quarterly_balance_sheet = _table(
            quarterly_period,
            **{"Total Assets": 370_000_000_000, "Total Debt": 99_000_000_000},
        )
        self.quarterly_cash_flow = _table(
            quarterly_period,
            **{"Operating Cash Flow": 31_000_000_000},
        )
        self.ttm_income_stmt = self.annual_income
        self.ttm_cash_flow = self.annual_cash_flow

    def get_income_stmt(self, *, freq: str) -> FakeTable:
        self.calls.append(("income", freq))
        return self.annual_income if freq == "yearly" else self.quarterly_income

    def get_balance_sheet(self, *, freq: str) -> FakeTable:
        self.calls.append(("balance", freq))
        return self.annual_balance if freq == "yearly" else self.quarterly_balance_sheet

    def get_cash_flow(self, *, freq: str) -> FakeTable:
        self.calls.append(("cash_flow", freq))
        return self.annual_cash_flow if freq == "yearly" else self.quarterly_cash_flow


class FakeYFinance:
    def __init__(self, ticker_type: type[FakeTicker] = FakeTicker) -> None:
        self._ticker_type = ticker_type
        self.tickers: list[FakeTicker] = []

    def Ticker(self, symbol: str) -> FakeTicker:
        ticker = self._ticker_type(symbol)
        self.tickers.append(ticker)
        return ticker


def _provider(fake: FakeYFinance | None = None) -> YahooFinancialStatementProvider:
    return YahooFinancialStatementProvider(
        fake or FakeYFinance(),
        clock=lambda: RETRIEVED_AT,
    )


def test_yahoo_provider_satisfies_financial_statement_contract() -> None:
    provider: FinancialStatementProvider = _provider()

    assert provider.name == "yahoo"


def test_yahoo_provider_maps_annual_bundle_without_fabricating_missing_values() -> None:
    provider = _provider()

    bundles = provider.get_financial_statement_bundle(
        FinancialStatementRequest("aapl", FinancialPeriodType.ANNUAL, limit=1)
    )

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle.symbol == "AAPL"
    assert bundle.source == "yahoo"
    assert bundle.retrieved_at == RETRIEVED_AT
    assert bundle.income_statement is not None
    assert bundle.income_statement.revenue == 410_000_000_000
    assert bundle.income_statement.eps_diluted == 6.42
    assert bundle.income_statement.cost_of_revenue is None
    assert bundle.balance_sheet is not None
    assert bundle.balance_sheet.total_assets == 365_000_000_000
    assert bundle.balance_sheet.current_assets is None
    assert bundle.cash_flow_statement is not None
    assert bundle.cash_flow_statement.free_cash_flow == 106_000_000_000
    assert bundle.income_statement.period.report_date == date(2025, 12, 31)


def test_yahoo_provider_maps_quarterly_period_and_frequency() -> None:
    fake = FakeYFinance()
    provider = _provider(fake)

    statements = provider.get_income_statement(
        FinancialStatementRequest("AAPL", FinancialPeriodType.QUARTERLY, limit=1)
    )

    assert statements[0].period.fiscal_year == 2026
    assert statements[0].period.fiscal_quarter == 2
    assert statements[0].revenue == 102_000_000_000
    assert fake.tickers[0].calls == [("income", "quarterly")]


def test_yahoo_provider_builds_partial_ttm_bundle() -> None:
    provider = _provider()

    bundles = provider.get_financial_statement_bundle(
        FinancialStatementRequest("AAPL", FinancialPeriodType.TRAILING_TWELVE_MONTHS, limit=1)
    )

    assert bundles[0].income_statement is not None
    assert bundles[0].balance_sheet is not None
    assert bundles[0].cash_flow_statement is not None
    assert (
        bundles[0].income_statement.period.period_type
        is FinancialPeriodType.TRAILING_TWELVE_MONTHS
    )


def test_yahoo_provider_wraps_complete_provider_failure() -> None:
    class FailingTicker(FakeTicker):
        def get_income_stmt(self, *, freq: str) -> FakeTable:
            raise RuntimeError("unavailable")

        def get_balance_sheet(self, *, freq: str) -> FakeTable:
            raise RuntimeError("unavailable")

        def get_cash_flow(self, *, freq: str) -> FakeTable:
            raise RuntimeError("unavailable")

    provider = _provider(FakeYFinance(FailingTicker))

    with pytest.raises(FinancialStatementProviderError, match="statements failed"):
        provider.get_financial_statement_bundle(
            FinancialStatementRequest("AAPL", FinancialPeriodType.ANNUAL, limit=1)
        )
