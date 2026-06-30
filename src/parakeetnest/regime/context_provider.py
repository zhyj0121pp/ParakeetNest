"""Economic regime context provider backed by the regime service boundary."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Protocol

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    EconomicRegimeContextSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.regime.models import (
    EconomicRegimeSnapshot,
    RegimeIndicator,
)


class _EconomicRegimeService(Protocol):
    """Minimal regime service contract consumed by the context provider."""

    def get_current_regime(
        self,
        *,
        as_of_date: date | None = None,
    ) -> EconomicRegimeSnapshot:
        """Return the current provider-neutral economic regime snapshot."""


class EconomicRegimeContextProvider:
    """Build prompt-ready economic regime context from regime snapshots."""

    provider_name = "economic_regime"

    def __init__(self, economic_regime_service: _EconomicRegimeService) -> None:
        self._economic_regime_service = economic_regime_service

    def supports(self, request: ContextRequest) -> bool:
        return request.include_macro

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        as_of_date = request.as_of.date() if request.as_of is not None else None
        snapshot = self._economic_regime_service.get_current_regime(
            as_of_date=as_of_date
        )
        fetched_at = request.as_of or datetime.combine(snapshot.as_of_date, time.min)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            economic_regime=EconomicRegimeContextSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                regime=snapshot.regime.value,
                confidence=snapshot.confidence.value,
                observed_on=snapshot.as_of_date,
                indicators=self._render_indicators(snapshot.indicators),
                summary=snapshot.summary,
                regime_source=snapshot.source,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "economic_regime_service"},
        )

    @classmethod
    def _render_indicators(
        cls,
        indicators: list[RegimeIndicator],
    ) -> tuple[str, ...]:
        return tuple(cls._render_indicator(indicator) for indicator in indicators)

    @staticmethod
    def _render_indicator(indicator: RegimeIndicator) -> str:
        fields = [
            f"{indicator.name} ({indicator.signal.value})",
        ]
        if indicator.value is not None:
            value = f"{indicator.value:g}"
            if indicator.unit:
                value = f"{value} {indicator.unit}"
            fields.append(value)
        if indicator.as_of_date is not None:
            fields.append(f"as of {indicator.as_of_date.isoformat()}")
        if indicator.interpretation:
            fields.append(indicator.interpretation)
        if len(fields) == 1:
            return fields[0]
        return ": ".join((fields[0], ", ".join(fields[1:])))


__all__ = ["EconomicRegimeContextProvider"]
