"""Plain-text market breadth context rendering."""

from __future__ import annotations

from parakeetnest.intelligence.market_breadth.service import MarketBreadthService


class MarketBreadthContextProvider:
    """Render market breadth snapshots as deterministic plain text."""

    def __init__(
        self,
        service: MarketBreadthService,
    ) -> None:
        self._service = service

    def build_context(
        self,
        universe: str,
    ) -> str:
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
