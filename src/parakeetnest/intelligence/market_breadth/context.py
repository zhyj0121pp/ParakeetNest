"""Market breadth context provider backed by the service boundary."""

from __future__ import annotations

from datetime import datetime, time
from typing import Protocol

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MarketBreadthContextSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.intelligence.market_breadth.models import MarketBreadthSnapshot


class _MarketBreadthService(Protocol):
    """Minimal market breadth service contract consumed by the provider."""

    def get_market_breadth(self, universe: str) -> MarketBreadthSnapshot:
        """Return the current provider-neutral market breadth snapshot."""


class MarketBreadthContextProvider:
    """Build prompt-ready market breadth context from service snapshots."""

    provider_name = "market_breadth"

    def __init__(
        self,
        service: _MarketBreadthService,
        *,
        default_universe: str = "SP500",
    ) -> None:
        self._service = service
        self._default_universe = default_universe

    def supports(self, request: ContextRequest) -> bool:
        return request.include_macro

    def build_context(
        self,
        request: ContextRequest | str,
    ) -> ContextProviderResult | str:
        """Return a context contribution or legacy plain-text context block."""
        if isinstance(request, str):
            return self._render_text_context(request)

        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        snapshot = self._service.get_market_breadth(self._default_universe)
        fetched_at = request.as_of or datetime.combine(snapshot.date, time.min)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
                warnings=snapshot.warnings,
            ),
            market_breadth=MarketBreadthContextSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                as_of_date=snapshot.date,
                universe=snapshot.universe,
                breadth_regime=snapshot.breadth_regime.value,
                breadth_score=snapshot.breadth_score,
                advancers=snapshot.advancers,
                decliners=snapshot.decliners,
                unchanged=snapshot.unchanged,
                new_highs=snapshot.new_highs,
                new_lows=snapshot.new_lows,
                percent_above_20d_ma=snapshot.percent_above_20d_ma,
                percent_above_50d_ma=snapshot.percent_above_50d_ma,
                percent_above_200d_ma=snapshot.percent_above_200d_ma,
                up_volume=snapshot.up_volume,
                down_volume=snapshot.down_volume,
                warnings=snapshot.warnings,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "market_breadth_service"},
        )

    def _render_text_context(self, universe: str) -> str:
        """Return a plain-text context block for the requested universe."""
        snapshot = self._service.get_market_breadth(universe)
        warnings = self._render_warnings(snapshot.warnings)

        lines = [
            "Market Breadth",
            "",
            f"Universe: {snapshot.universe}",
            "",
            f"Breadth Regime: {snapshot.breadth_regime.value.upper()}",
            "",
            f"Breadth Score: {snapshot.breadth_score:g}",
            "",
            "Advance/Decline:",
            f"{snapshot.advancers} / {snapshot.decliners}",
            "",
            "New Highs/New Lows:",
            f"{snapshot.new_highs} / {snapshot.new_lows}",
            "",
            "Above 20DMA:",
            f"{snapshot.percent_above_20d_ma:g}%",
            "",
            "Above 50DMA:",
            f"{snapshot.percent_above_50d_ma:g}%",
            "",
            "Above 200DMA:",
            f"{snapshot.percent_above_200d_ma:g}%",
            "",
            "Up Volume:",
            self._render_number(snapshot.up_volume),
            "",
            "Down Volume:",
            self._render_number(snapshot.down_volume),
            "",
            "Warnings:",
            *warnings,
        ]
        return "\n".join(lines)

    @staticmethod
    def _render_warnings(warnings: tuple[str, ...]) -> list[str]:
        if not warnings:
            return ["None"]
        return [f"- {warning}" for warning in warnings]

    @staticmethod
    def _render_number(value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"


__all__ = ["MarketBreadthContextProvider"]
