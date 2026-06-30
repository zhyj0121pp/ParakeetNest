"""Deterministic mock provider for Momentum Layer intelligence."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.momentum.provider import MomentumInputs


class MockMomentumProvider:
    """Deterministic network-free provider for tests and local development."""

    def __init__(self, inputs: dict[str, MomentumInputs] | None = None) -> None:
        self._inputs = {
            symbol.strip().upper(): value for symbol, value in (inputs or {}).items()
        }
        self.calls: list[tuple[str, date | None]] = []

    def get_momentum_inputs(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumInputs:
        """Return injected inputs or deterministic sample momentum facts."""
        self.calls.append((symbol, as_of))

        normalized_symbol = symbol.strip().upper()
        if normalized_symbol in self._inputs:
            return self._inputs[normalized_symbol]

        observed_on = as_of or date(2026, 6, 30)
        return MomentumInputs(
            symbol=normalized_symbol,
            as_of=observed_on,
            price_change_1m=0.043,
            price_change_3m=0.118,
            price_change_6m=0.247,
            relative_strength=82.5,
            trend_strength=0.76,
        )


__all__ = ["MockMomentumProvider"]
