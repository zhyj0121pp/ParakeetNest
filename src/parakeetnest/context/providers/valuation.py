"""Valuation context provider backed by the Valuation Layer service."""

from __future__ import annotations

from collections.abc import Callable

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    FinancialStatementSnapshot,
    MarketSnapshot,
    MeetingContext,
    ValuationContextItem,
    ValuationContextSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.valuation.models import (
    ValuationInput,
    ValuationSnapshot,
)
from parakeetnest.valuation.input_builder import (
    ValuationInputBuilder as DefaultValuationInputBuilder,
)
from parakeetnest.valuation.service import ValuationService


ValuationInputBuilder = Callable[
    [
        str,
        ContextRequest,
        MarketSnapshot | None,
        FinancialStatementSnapshot | None,
    ],
    ValuationInput,
]


class ValuationContextProvider:
    """Build neutral context from service-backed valuation snapshots."""

    provider_name = "valuation"

    def __init__(
        self,
        valuation_service: ValuationService,
        *,
        input_builder: ValuationInputBuilder | None = None,
        market: MarketSnapshot | None = None,
        financials: FinancialStatementSnapshot | None = None,
    ) -> None:
        self._valuation_service = valuation_service
        self._input_builder = input_builder or DefaultValuationInputBuilder()
        self._market = market
        self._financials = financials

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        snapshots = tuple(
            self._valuation_service.create_snapshot(
                self._valuation_input_for(symbol, request)
            )
            for symbol in request.symbols
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=request.as_of,
                sources=(self.provider_name,),
            ),
            valuation=ValuationContextSnapshot(
                source=self.provider_name,
                fetched_at=request.as_of,
                items=tuple(self._item_for(snapshot) for snapshot in snapshots),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "valuation_service"},
        )

    def _valuation_input_for(
        self,
        symbol: str,
        request: ContextRequest,
    ) -> ValuationInput:
        return self._input_builder(
            symbol,
            request,
            self._market,
            self._financials,
        )

    @staticmethod
    def _item_for(snapshot: ValuationSnapshot) -> ValuationContextItem:
        return ValuationContextItem(
            symbol=snapshot.symbol,
            as_of_date=snapshot.as_of_date,
            fiscal_period=snapshot.fiscal_period,
            metrics={
                metric.value: value for metric, value in snapshot.metrics.items()
            },
            calculation_notes=tuple(snapshot.calculation_notes),
            confidence=snapshot.confidence.value,
            data_sources=tuple(snapshot.data_sources),
        )


__all__ = ["ValuationContextProvider", "ValuationInputBuilder"]
