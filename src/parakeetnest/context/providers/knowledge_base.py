"""Deterministic mock knowledge base context provider."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    KnowledgeBaseSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)


class KnowledgeBaseContextProvider:
    """Build fixed remembered research context."""

    provider_name = "mock_knowledge_base"
    _fetched_at = datetime(2026, 6, 29, 13, 20, tzinfo=UTC)

    def supports(self, request: ContextRequest) -> bool:
        return request.include_knowledge_base

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=self._fetched_at,
                sources=(self.provider_name,),
            ),
            knowledge_base=KnowledgeBaseSnapshot(
                source=self.provider_name,
                fetched_at=self._fetched_at,
                thesis=(
                    "Own AI infrastructure leaders when revenue visibility improves.",
                    "Require margin evidence before increasing cyclical semiconductor exposure.",
                ),
                discussions=(
                    "Prior committee debate favored patience on valuation-sensitive entries.",
                    "Risk review emphasized position sizing around earnings catalysts.",
                ),
                research_notes=(
                    "Watch data center backlog commentary.",
                    "Compare free cash flow conversion against capex intensity.",
                ),
                lessons_learned=(
                    "Check memory before debating fresh catalysts.",
                    "Separate durable thesis changes from single-quarter noise.",
                ),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"fixture": "knowledge_base"},
        )
