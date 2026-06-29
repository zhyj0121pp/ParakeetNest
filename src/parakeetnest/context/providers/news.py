"""Deterministic mock news context provider."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    NewsItem,
    NewsSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)


class NewsContextProvider:
    """Build fixed news snapshots for requested symbols."""

    provider_name = "mock_news"
    _fetched_at = datetime(2026, 6, 29, 13, 5, tzinfo=UTC)
    _published_at = datetime(2026, 6, 28, 14, 30, tzinfo=UTC)
    _fixtures = {
        "AMD": (
            "AMD expands AI accelerator roadmap",
            "Roadmap update highlights data center GPU demand and execution milestones.",
        ),
        "NVDA": (
            "NVIDIA supply chain checks remain constructive",
            "Channel commentary points to continued accelerator backlog visibility.",
        ),
    }
    _fallback = (
        "Requested symbol appears in mock market watchlist",
        "Deterministic placeholder item used for Context Layer exercise.",
    )

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        items = tuple(self._item_for(symbol) for symbol in request.symbols)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=self._fetched_at,
                sources=(self.provider_name,),
            ),
            news=NewsSnapshot(
                source=self.provider_name,
                fetched_at=self._fetched_at,
                items=items,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"fixture": "news"},
        )

    def _item_for(self, symbol: str) -> NewsItem:
        title, summary = self._fixtures.get(symbol, self._fallback)
        return NewsItem(
            title=title,
            source=self.provider_name,
            symbol=symbol,
            summary=summary,
            published_at=self._published_at,
        )
