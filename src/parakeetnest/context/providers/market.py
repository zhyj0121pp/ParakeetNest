"""Market context provider backed by the Market Data Layer."""

from __future__ import annotations

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.market_data.errors import MarketDataError
from parakeetnest.market_data.models import CompanyInfo, MarketDataSnapshot, Symbol
from parakeetnest.market_data.service import MarketDataService


class MarketContextProvider:
    """Build market context from provider-backed market data service snapshots."""

    provider_name = "market_data"

    def __init__(self, market_data_service: MarketDataService) -> None:
        self._market_data_service = market_data_service

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        snapshots = tuple(
            self._market_data_service.get_snapshot(Symbol(symbol))
            for symbol in request.symbols
        )
        fetched_at = max((snapshot.timestamp for snapshot in snapshots), default=None)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            market=MarketSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                points=tuple(self._point_for(snapshot) for snapshot in snapshots),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "market_data_service"},
        )

    def _point_for(self, snapshot: MarketDataSnapshot) -> MarketDataPoint:
        daily_change = self._daily_change(snapshot)
        company_info = self._company_info_for(snapshot.symbol)
        return MarketDataPoint(
            symbol=snapshot.symbol.ticker,
            source=self.provider_name,
            observed_at=snapshot.timestamp,
            price=snapshot.price,
            daily_change=daily_change,
            daily_change_percent=self._daily_change_percent(snapshot, daily_change),
            volume=snapshot.volume,
            market_cap=company_info.market_cap if company_info is not None else None,
            pe_ratio=(
                company_info.trailing_pe if company_info is not None else None
            ),
            sector=company_info.sector if company_info is not None else None,
            industry=company_info.industry if company_info is not None else None,
            beta=company_info.beta if company_info is not None else None,
            forward_pe=company_info.forward_pe if company_info is not None else None,
            enterprise_value=(
                company_info.enterprise_value if company_info is not None else None
            ),
            revenue_ttm=company_info.revenue_ttm if company_info is not None else None,
            ev_to_sales=company_info.ev_to_sales if company_info is not None else None,
        )

    def _company_info_for(self, symbol: Symbol) -> CompanyInfo | None:
        try:
            return self._market_data_service.get_company_info(symbol)
        except (AttributeError, MarketDataError):
            return None

    @staticmethod
    def _daily_change(snapshot: MarketDataSnapshot) -> float | None:
        if snapshot.previous_close is None:
            return None
        return snapshot.price - snapshot.previous_close

    @staticmethod
    def _daily_change_percent(
        snapshot: MarketDataSnapshot,
        daily_change: float | None,
    ) -> float | None:
        if daily_change is None or snapshot.previous_close in (None, 0):
            return None
        return (daily_change / snapshot.previous_close) * 100
