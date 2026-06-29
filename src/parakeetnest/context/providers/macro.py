"""Deterministic mock macro context provider."""

from __future__ import annotations

from datetime import UTC, date, datetime

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MacroSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)


class MacroContextProvider:
    """Build a fixed macro snapshot."""

    provider_name = "mock_macro"
    _fetched_at = datetime(2026, 6, 29, 13, 15, tzinfo=UTC)
    _observed_on = date(2026, 6, 26)

    def supports(self, request: ContextRequest) -> bool:
        return request.include_macro

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=self._fetched_at,
                sources=(self.provider_name,),
            ),
            macro=MacroSnapshot(
                source=self.provider_name,
                fetched_at=self._fetched_at,
                indicators=(
                    "Policy rates remain restrictive.",
                    "Credit spreads are stable versus the prior mock reading.",
                    "Semiconductor capex expectations remain constructive.",
                ),
                observed_on=self._observed_on,
                summary="Mock macro backdrop is neutral-to-constructive for risk assets.",
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"fixture": "macro"},
        )
