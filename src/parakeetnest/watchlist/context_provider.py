"""Watchlist context provider backed by WatchlistIntelligenceService."""

from __future__ import annotations

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    WatchlistContextItem,
    WatchlistContextSnapshot,
)
from parakeetnest.context.provider import ContextProviderResult
from parakeetnest.watchlist.models import WatchlistInsight
from parakeetnest.watchlist.service import WatchlistIntelligenceService


class WatchlistContextProvider:
    """Expose active watchlist insights through the Context Layer."""

    provider_name = "watchlist"

    def __init__(
        self,
        watchlist_intelligence_service: WatchlistIntelligenceService,
    ) -> None:
        self._watchlist_intelligence_service = watchlist_intelligence_service

    def supports(self, request: ContextRequest) -> bool:
        return True

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        insights = tuple(
            sorted(
                self._watchlist_intelligence_service.build_all_insights(),
                key=lambda insight: insight.symbol,
            )
        )
        fetched_at = request.as_of
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            watchlist=WatchlistContextSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                items=tuple(self._item_for(insight) for insight in insights),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "watchlist_intelligence_service"},
        )

    @staticmethod
    def _item_for(insight: WatchlistInsight) -> WatchlistContextItem:
        return WatchlistContextItem(
            symbol=insight.symbol,
            summary=insight.summary,
            bullish_factors=insight.bullish_factors,
            bearish_factors=insight.bearish_factors,
            open_questions=insight.open_questions,
            recommended_action=insight.recommended_action,
        )


__all__ = ["WatchlistContextProvider"]
