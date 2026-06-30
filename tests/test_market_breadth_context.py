"""Tests for plain-text Market Breadth context rendering."""

from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.market_breadth import (
    BreadthRegime,
    MarketBreadthContextProvider,
    MarketBreadthSnapshot,
)
from parakeetnest.intelligence.market_breadth.context import (
    MarketBreadthContextProvider as DirectMarketBreadthContextProvider,
)


SNAPSHOT_DATE = date(2026, 6, 30)


class RecordingMarketBreadthService:
    """Market breadth service test double that records context requests."""

    def __init__(self, snapshot: MarketBreadthSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[str] = []

    def get_market_breadth(self, universe: str) -> MarketBreadthSnapshot:
        self.calls.append(universe)
        return self.snapshot


def snapshot(
    *,
    warnings: tuple[str, ...] = (),
) -> MarketBreadthSnapshot:
    """Build one provider-neutral breadth snapshot for context tests."""
    return MarketBreadthSnapshot(
        universe="sp500",
        date=SNAPSHOT_DATE,
        advancers=320,
        decliners=180,
        unchanged=0,
        new_highs=48,
        new_lows=12,
        percent_above_20d_ma=72,
        percent_above_50d_ma=68,
        percent_above_200d_ma=61,
        up_volume=5_200_000_000,
        down_volume=2_100_000_000,
        breadth_score=0.72,
        breadth_regime=BreadthRegime.HEALTHY,
        warnings=warnings,
    )


def test_context_provider_calls_service_once() -> None:
    """The context provider should request exactly one service snapshot."""
    service = RecordingMarketBreadthService(snapshot())
    provider = MarketBreadthContextProvider(service)

    provider.build_context("SP500")

    assert service.calls == ["SP500"]


def test_output_contains_all_important_fields() -> None:
    """The rendered context should include the breadth snapshot fields."""
    provider = MarketBreadthContextProvider(
        RecordingMarketBreadthService(snapshot(warnings=("partial volume data",)))
    )

    context = provider.build_context("SP500")

    assert "Market Breadth" in context
    assert "Universe: SP500" in context
    assert "Breadth Regime: HEALTHY" in context
    assert "Breadth Score: 0.72" in context
    assert "Advance/Decline:\n320 / 180" in context
    assert "New Highs/New Lows:\n48 / 12" in context
    assert "Above 20DMA:\n72%" in context
    assert "Above 50DMA:\n68%" in context
    assert "Above 200DMA:\n61%" in context
    assert "Up Volume:\n5200000000" in context
    assert "Down Volume:\n2100000000" in context
    assert "Warnings:\n- partial volume data" in context


def test_empty_warnings_render_none() -> None:
    """Empty warning lists should render as an explicit None."""
    provider = MarketBreadthContextProvider(RecordingMarketBreadthService(snapshot()))

    context = provider.build_context("SP500")

    assert "Warnings:\nNone" in context


def test_multiple_warnings_render_in_order() -> None:
    """Warning order should remain stable and snapshot-driven."""
    provider = MarketBreadthContextProvider(
        RecordingMarketBreadthService(
            snapshot(
                warnings=(
                    "breadth participation is narrowing",
                    "new lows are elevated",
                )
            )
        )
    )

    context = provider.build_context("SP500")

    assert (
        "Warnings:\n- breadth participation is narrowing\n- new lows are elevated"
        in context
    )


def test_context_rendering_is_deterministic() -> None:
    """Rendering the same snapshot repeatedly should produce identical text."""
    provider = MarketBreadthContextProvider(RecordingMarketBreadthService(snapshot()))

    first = provider.build_context("SP500")
    second = provider.build_context("SP500")

    assert first == second


def test_market_breadth_package_exports_context_provider() -> None:
    """The package should expose the public context provider."""
    import parakeetnest.intelligence.market_breadth as market_breadth

    assert market_breadth.MarketBreadthContextProvider is MarketBreadthContextProvider
    assert MarketBreadthContextProvider is DirectMarketBreadthContextProvider
