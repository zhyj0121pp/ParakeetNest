"""Tests for FinancialStatementContextProvider service-backed behavior."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from parakeetnest.context import (
    ContextRequest,
    MeetingContextPromptRenderer,
    UnsupportedContextRequestError,
)
from parakeetnest.context.providers import FinancialStatementContextProvider
from parakeetnest.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementRequest,
    FinancialStatementProviderError,
    IncomeStatement,
)


class RecordingFinancialStatementService:
    """Financial statement service test double that records bundle requests."""

    def __init__(
        self,
        bundles_by_request: dict[
            tuple[str, FinancialPeriodType], list[FinancialStatementBundle]
        ]
        | None = None,
    ) -> None:
        self.bundles_by_request = bundles_by_request or {}
        self.calls: list[FinancialStatementRequest] = []

    def get_financial_statement_bundle(
        self,
        request: FinancialStatementRequest,
    ) -> list[FinancialStatementBundle]:
        self.calls.append(request)
        return self.bundles_by_request.get((request.symbol, request.period_type), [])


def _period(
    symbol: str,
    period_type: FinancialPeriodType,
    *,
    fiscal_year: int = 2026,
    fiscal_quarter: int | None = None,
) -> FinancialStatementPeriod:
    return FinancialStatementPeriod(
        symbol=symbol,
        period_type=period_type,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        start_date=date(fiscal_year, 1, 1),
        end_date=date(fiscal_year, 12, 31),
        report_date=date(fiscal_year, 12, 31),
        currency="USD",
    )


def _bundle(
    symbol: str,
    period_type: FinancialPeriodType,
    *,
    fiscal_year: int = 2026,
    fiscal_quarter: int | None = None,
    revenue: float = 100.0,
    source: str = "mock",
    retrieved_at: datetime | None = None,
) -> FinancialStatementBundle:
    period = _period(
        symbol,
        period_type,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
    )
    return FinancialStatementBundle(
        symbol=symbol,
        income_statement=IncomeStatement(
            period=period,
            revenue=revenue,
            gross_profit=60.0,
            operating_income=30.0,
            net_income=20.0,
            eps_basic=2.0,
            eps_diluted=1.9,
            source=source,
            retrieved_at=retrieved_at,
        ),
        balance_sheet=BalanceSheet(
            period=period,
            cash_and_equivalents=10.0,
            total_debt=5.0,
            total_equity=50.0,
            source=source,
            retrieved_at=retrieved_at,
        ),
        cash_flow_statement=CashFlowStatement(
            period=period,
            operating_cash_flow=25.0,
            free_cash_flow=18.0,
            source=source,
            retrieved_at=retrieved_at,
        ),
        source=source,
        retrieved_at=retrieved_at,
    )


def test_financial_statement_context_provider_supports_symbol_requests_only() -> None:
    provider = FinancialStatementContextProvider(RecordingFinancialStatementService())

    assert provider.supports(ContextRequest("Review AMD.", ("AMD",))) is True
    assert provider.supports(ContextRequest("Review the market.", ())) is False


def test_financial_statement_context_provider_builds_context_from_bundles() -> None:
    retrieved_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    service = RecordingFinancialStatementService(
        {
            ("AMD", FinancialPeriodType.ANNUAL): [
                _bundle(
                    "AMD",
                    FinancialPeriodType.ANNUAL,
                    fiscal_year=2026,
                    retrieved_at=retrieved_at,
                )
            ],
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = FinancialStatementContextProvider(service).build_context(request)

    assert [
        (call.symbol, call.period_type, call.limit) for call in service.calls
    ] == [
        ("AMD", FinancialPeriodType.ANNUAL, 1),
        ("AMD", FinancialPeriodType.QUARTERLY, 1),
        ("AMD", FinancialPeriodType.TRAILING_TWELVE_MONTHS, 1),
    ]
    assert result.provider_name == "financial_statements"
    assert result.metadata == {"source": "financial_statement_service"}
    assert result.partial_context.financials is not None
    assert result.partial_context.financials.source == "financial_statements"
    assert result.partial_context.financials.fetched_at == retrieved_at

    item = result.partial_context.financials.items[0]
    assert item.symbol == "AMD"
    assert item.period_type == "annual"
    assert item.revenue == 100.0
    assert item.gross_profit == 60.0
    assert item.operating_income == 30.0
    assert item.net_income == 20.0
    assert item.eps == 1.9
    assert item.cash == 10.0
    assert item.total_debt == 5.0
    assert item.total_equity == 50.0
    assert item.operating_cash_flow == 25.0
    assert item.free_cash_flow == 18.0
    assert item.fiscal_year == 2026
    assert item.fiscal_quarter is None
    assert item.currency == "USD"
    assert item.source == "mock"


def test_financial_statement_context_provider_is_provider_neutral() -> None:
    service = RecordingFinancialStatementService(
        {
            ("AMD", FinancialPeriodType.ANNUAL): [
                _bundle("AMD", FinancialPeriodType.ANNUAL)
            ],
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = FinancialStatementContextProvider(service).build_context(request)

    assert result.partial_context.financials is not None
    item = result.partial_context.financials.items[0]
    assert not isinstance(item, FinancialStatementBundle)
    assert not hasattr(item, "income_statement")
    assert not hasattr(item, "balance_sheet")
    assert not hasattr(item, "cash_flow_statement")


def test_financial_statement_context_provider_renders_bundles() -> None:
    fetched_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    service = RecordingFinancialStatementService(
        {
            ("AMD", FinancialPeriodType.ANNUAL): [
                _bundle(
                    "AMD",
                    FinancialPeriodType.ANNUAL,
                    retrieved_at=fetched_at,
                )
            ],
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    result = FinancialStatementContextProvider(service).build_context(request)

    rendered = MeetingContextPromptRenderer().render(result.partial_context)

    assert "## Financial Statements" in rendered
    assert "- AMD annual: revenue=100.0" in rendered
    assert "eps=1.9" in rendered
    assert "free_cash_flow=18.0" in rendered
    assert "fiscal_year=2026" in rendered
    assert "source=mock" in rendered


def test_financial_statement_context_provider_includes_annual_quarterly_and_ttm() -> None:
    service = RecordingFinancialStatementService(
        {
            ("AMD", FinancialPeriodType.ANNUAL): [
                _bundle("AMD", FinancialPeriodType.ANNUAL, fiscal_year=2026)
            ],
            ("AMD", FinancialPeriodType.QUARTERLY): [
                _bundle(
                    "AMD",
                    FinancialPeriodType.QUARTERLY,
                    fiscal_year=2026,
                    fiscal_quarter=2,
                    revenue=40.0,
                )
            ],
            ("AMD", FinancialPeriodType.TRAILING_TWELVE_MONTHS): [
                _bundle(
                    "AMD",
                    FinancialPeriodType.TRAILING_TWELVE_MONTHS,
                    fiscal_year=2026,
                    revenue=120.0,
                )
            ],
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = FinancialStatementContextProvider(service).build_context(request)

    assert result.partial_context.financials is not None
    assert [item.period_type for item in result.partial_context.financials.items] == [
        "annual",
        "quarterly",
        "ttm",
    ]
    assert result.partial_context.financials.items[1].fiscal_quarter == 2
    assert result.partial_context.financials.items[2].revenue == 120.0


def test_financial_statement_context_provider_preserves_empty_result() -> None:
    service = RecordingFinancialStatementService()
    as_of = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    request = ContextRequest("Review POET.", ("POET",), as_of=as_of)

    result = FinancialStatementContextProvider(service).build_context(request)

    assert result.partial_context.financials is not None
    assert result.partial_context.financials.items == ()
    assert result.partial_context.financials.fetched_at == as_of


def test_financial_statement_context_provider_preserves_partial_results_on_failure() -> None:
    class PartiallyFailingService(RecordingFinancialStatementService):
        def get_financial_statement_bundle(
            self,
            request: FinancialStatementRequest,
        ) -> list[FinancialStatementBundle]:
            if request.symbol == "BROKEN":
                raise FinancialStatementProviderError("Yahoo unavailable")
            return super().get_financial_statement_bundle(request)

    service = PartiallyFailingService(
        {
            ("NVDA", FinancialPeriodType.ANNUAL): [
                _bundle("NVDA", FinancialPeriodType.ANNUAL, revenue=200.0)
            ],
        }
    )
    request = ContextRequest("Review NVDA and BROKEN.", ("NVDA", "BROKEN"))

    result = FinancialStatementContextProvider(service).build_context(request)

    assert result.partial_context.financials is not None
    assert [item.symbol for item in result.partial_context.financials.items] == ["NVDA"]
    assert len(result.errors) == 3
    assert all("BROKEN" in error for error in result.errors)


def test_financial_statement_context_provider_handles_multiple_bundles() -> None:
    service = RecordingFinancialStatementService(
        {
            ("AMD", FinancialPeriodType.ANNUAL): [
                _bundle("AMD", FinancialPeriodType.ANNUAL, revenue=100.0),
                _bundle(
                    "AMD",
                    FinancialPeriodType.ANNUAL,
                    fiscal_year=2025,
                    revenue=90.0,
                ),
            ],
            ("NVDA", FinancialPeriodType.ANNUAL): [
                _bundle("NVDA", FinancialPeriodType.ANNUAL, revenue=200.0)
            ],
        }
    )
    request = ContextRequest("Review AMD and NVDA.", ("AMD", "NVDA"))

    result = FinancialStatementContextProvider(service).build_context(request)

    assert result.partial_context.financials is not None
    assert [
        (item.symbol, item.period_type, item.fiscal_year, item.revenue)
        for item in result.partial_context.financials.items
    ] == [
        ("AMD", "annual", 2026, 100.0),
        ("AMD", "annual", 2025, 90.0),
        ("NVDA", "annual", 2026, 200.0),
    ]


def test_financial_statement_context_provider_rejects_requests_without_symbols() -> None:
    service = RecordingFinancialStatementService()
    provider = FinancialStatementContextProvider(service)
    request = ContextRequest(question="Review the market.", symbols=())

    with pytest.raises(UnsupportedContextRequestError):
        provider.build_context(request)

    assert service.calls == []
