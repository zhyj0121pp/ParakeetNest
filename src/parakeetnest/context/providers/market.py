"""Deterministic mock market context provider."""

from __future__ import annotations

from datetime import UTC, datetime

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


class MarketContextProvider:
    """Build fixed market snapshots for requested symbols."""

    provider_name = "mock_market"
    _fetched_at = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    _fixtures = {
        "AMD": {
            "price": 175.25,
            "daily_change": 2.15,
            "daily_change_percent": 1.24,
            "volume": 48200000.0,
            "market_cap": 284000000000.0,
            "pe_ratio": 41.8,
            "eps": 4.19,
        },
        "NVDA": {
            "price": 128.40,
            "daily_change": -0.75,
            "daily_change_percent": -0.58,
            "volume": 205000000.0,
            "market_cap": 3160000000000.0,
            "pe_ratio": 36.4,
            "eps": 3.53,
        },
    }
    _fallback = {
        "price": 100.0,
        "daily_change": 0.0,
        "daily_change_percent": 0.0,
        "volume": 1000000.0,
        "market_cap": 10000000000.0,
        "pe_ratio": 20.0,
        "eps": 5.0,
    }

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        points = tuple(self._point_for(symbol) for symbol in request.symbols)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=self._fetched_at,
                sources=(self.provider_name,),
            ),
            market=MarketSnapshot(
                source=self.provider_name,
                fetched_at=self._fetched_at,
                points=points,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"fixture": "market"},
        )

    def _point_for(self, symbol: str) -> MarketDataPoint:
        values = self._fixtures.get(symbol, self._fallback)
        return MarketDataPoint(
            symbol=symbol,
            source=self.provider_name,
            observed_at=self._fetched_at,
            **values,
        )
