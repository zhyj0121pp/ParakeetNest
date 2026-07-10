"""Financial statement context provider backed by the Financial Statement Layer."""

from __future__ import annotations

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    FinancialStatementItem,
    FinancialStatementSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.financials.models import (
    FinancialPeriodType,
    FinancialStatementBundle,
    FinancialStatementPeriod,
    FinancialStatementRequest,
)
from parakeetnest.financials.provider import FinancialStatementProviderError
from parakeetnest.financials.service import FinancialStatementService


class FinancialStatementContextProvider:
    """Build neutral context from provider-backed financial statement bundles."""

    provider_name = "financial_statements"
    _PERIOD_TYPES = (
        FinancialPeriodType.ANNUAL,
        FinancialPeriodType.QUARTERLY,
        FinancialPeriodType.TRAILING_TWELVE_MONTHS,
    )

    def __init__(
        self,
        financial_statement_service: FinancialStatementService,
    ) -> None:
        self._financial_statement_service = financial_statement_service

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        bundles, errors = self._bundles_for_request(request)
        fetched_at = request.as_of or max(
            (bundle.retrieved_at for bundle in bundles if bundle.retrieved_at),
            default=None,
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            financials=FinancialStatementSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                items=tuple(self._item_for(bundle) for bundle in bundles),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "financial_statement_service"},
            errors=errors,
        )

    def _bundles_for_request(
        self,
        request: ContextRequest,
    ) -> tuple[tuple[FinancialStatementBundle, ...], tuple[str, ...]]:
        bundles: list[FinancialStatementBundle] = []
        errors: list[str] = []
        for symbol in request.symbols:
            for period_type in self._PERIOD_TYPES:
                try:
                    bundles.extend(
                        self._financial_statement_service.get_financial_statement_bundle(
                            FinancialStatementRequest(
                                symbol=symbol,
                                period_type=period_type,
                                limit=1,
                            )
                        )
                    )
                except FinancialStatementProviderError as exc:
                    errors.append(f"{symbol} {period_type.value}: {exc}")
        return tuple(bundles), tuple(errors)

    def _item_for(
        self,
        bundle: FinancialStatementBundle,
    ) -> FinancialStatementItem:
        income_statement = bundle.income_statement
        balance_sheet = bundle.balance_sheet
        cash_flow_statement = bundle.cash_flow_statement
        period = self._period_for(bundle)

        return FinancialStatementItem(
            symbol=bundle.symbol,
            period_type=period.period_type.value if period else "unknown",
            source=self._source_for(bundle),
            revenue=income_statement.revenue if income_statement else None,
            gross_profit=income_statement.gross_profit if income_statement else None,
            operating_income=(
                income_statement.operating_income if income_statement else None
            ),
            net_income=income_statement.net_income if income_statement else None,
            eps=self._eps_for(bundle),
            cash=balance_sheet.cash_and_equivalents if balance_sheet else None,
            total_debt=balance_sheet.total_debt if balance_sheet else None,
            total_equity=balance_sheet.total_equity if balance_sheet else None,
            operating_cash_flow=(
                cash_flow_statement.operating_cash_flow
                if cash_flow_statement
                else None
            ),
            free_cash_flow=(
                cash_flow_statement.free_cash_flow if cash_flow_statement else None
            ),
            fiscal_year=period.fiscal_year if period else None,
            fiscal_quarter=period.fiscal_quarter if period else None,
            currency=period.currency if period else None,
        )

    @staticmethod
    def _period_for(
        bundle: FinancialStatementBundle,
    ) -> FinancialStatementPeriod | None:
        if bundle.income_statement is not None:
            return bundle.income_statement.period
        if bundle.balance_sheet is not None:
            return bundle.balance_sheet.period
        if bundle.cash_flow_statement is not None:
            return bundle.cash_flow_statement.period
        return None

    @staticmethod
    def _eps_for(bundle: FinancialStatementBundle) -> float | None:
        income_statement = bundle.income_statement
        if income_statement is None:
            return None
        if income_statement.eps_diluted is not None:
            return income_statement.eps_diluted
        return income_statement.eps_basic

    @classmethod
    def _source_for(cls, bundle: FinancialStatementBundle) -> str:
        if bundle.source:
            return bundle.source
        if bundle.income_statement and bundle.income_statement.source:
            return bundle.income_statement.source
        if bundle.balance_sheet and bundle.balance_sheet.source:
            return bundle.balance_sheet.source
        if bundle.cash_flow_statement and bundle.cash_flow_statement.source:
            return bundle.cash_flow_statement.source
        return cls.provider_name


__all__ = ["FinancialStatementContextProvider"]
