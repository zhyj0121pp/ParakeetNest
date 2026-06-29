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
from parakeetnest.market_data.models import MarketDataSnapshot, Symbol
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
        return MarketDataPoint(
            symbol=snapshot.symbol.ticker,
            source=self.provider_name,
            observed_at=snapshot.timestamp,
            price=snapshot.price,
            daily_change=daily_change,
            daily_change_percent=self._daily_change_percent(snapshot, daily_change),
            volume=snapshot.volume,
        )

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
