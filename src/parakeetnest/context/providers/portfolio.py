"""Deterministic mock portfolio context provider."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    PortfolioPosition,
    PortfolioSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)


class PortfolioContextProvider:
    """Build a fixed portfolio snapshot for requested symbols."""

    provider_name = "mock_portfolio"
    _fetched_at = datetime(2026, 6, 29, 13, 10, tzinfo=UTC)
    _fixtures = {
        "AMD": PortfolioPosition(
            symbol="AMD",
            quantity=12.0,
            market_value=2103.0,
            cost_basis=1680.0,
            unrealized_pl=423.0,
            weight=0.084,
        ),
        "NVDA": PortfolioPosition(
            symbol="NVDA",
            quantity=8.0,
            market_value=1027.2,
            cost_basis=912.0,
            unrealized_pl=115.2,
            weight=0.041,
        ),
    }

    def supports(self, request: ContextRequest) -> bool:
        return request.include_portfolio and bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        positions = tuple(
            self._fixtures[symbol]
            for symbol in request.symbols
            if symbol in self._fixtures
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=self._fetched_at,
                sources=(self.provider_name,),
            ),
            portfolio=PortfolioSnapshot(
                source=self.provider_name,
                fetched_at=self._fetched_at,
                positions=positions,
                cash_balance=7500.0,
                total_value=25000.0,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"fixture": "portfolio"},
        )
