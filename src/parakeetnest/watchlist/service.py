"""Provider-neutral watchlist insight synthesis service."""

from __future__ import annotations

from collections.abc import Iterable

from parakeetnest.watchlist.models import (
    WatchlistInsight,
    WatchlistItem,
    WatchlistSignal,
    WatchlistStatus,
    WatchlistThesis,
)
from parakeetnest.watchlist.repository import (
    WatchlistRepository,
    normalize_watchlist_symbol,
)


class WatchlistIntelligenceService:
    """Build committee-ready watchlist insights from repository data."""

    def __init__(self, repository: WatchlistRepository) -> None:
        self._repository = repository

    def build_insight(
        self,
        symbol: str,
        theses: Iterable[WatchlistThesis] = (),
        signals: Iterable[WatchlistSignal] = (),
    ) -> WatchlistInsight:
        """Build one insight for a watchlist symbol."""
        normalized = normalize_watchlist_symbol(symbol)
        item = self._repository.get_item(normalized)
        if item is None:
            raise ValueError(f"watchlist item does not exist for {normalized}")

        grouped_theses = _group_theses_by_symbol(theses)
        grouped_signals = _group_signals_by_symbol(signals)
        return self._build_insight(
            item,
            grouped_theses.get(normalized, ()),
            grouped_signals.get(normalized, ()),
        )

    def build_all_insights(
        self,
        theses: Iterable[WatchlistThesis] = (),
        signals: Iterable[WatchlistSignal] = (),
    ) -> tuple[WatchlistInsight, ...]:
        """Build active insights for all non-archived watchlist items."""
        grouped_theses = _group_theses_by_symbol(theses)
        grouped_signals = _group_signals_by_symbol(signals)
        insights = []
        for item in self._repository.list_items():
            if item.status is WatchlistStatus.ARCHIVED:
                continue
            insights.append(
                self._build_insight(
                    item,
                    grouped_theses.get(item.symbol, ()),
                    grouped_signals.get(item.symbol, ()),
                )
            )
        return tuple(sorted(insights, key=lambda insight: insight.symbol))

    def _build_insight(
        self,
        item: WatchlistItem,
        theses: tuple[WatchlistThesis, ...],
        signals: tuple[WatchlistSignal, ...],
    ) -> WatchlistInsight:
        thesis = theses[0] if theses else None
        positive_signals = tuple(signal for signal in signals if signal.strength >= 0)
        negative_signals = tuple(signal for signal in signals if signal.strength < 0)

        open_questions: list[str] = []
        if thesis is None:
            open_questions.append("Document watchlist thesis.")
        if not signals:
            open_questions.append("Add current watchlist signals.")

        return WatchlistInsight(
            symbol=item.symbol,
            summary=_build_summary(item, thesis),
            bullish_factors=_build_bullish_factors(thesis, positive_signals),
            bearish_factors=_build_bearish_factors(thesis, negative_signals),
            open_questions=tuple(open_questions),
            recommended_action=_recommended_action(item, thesis),
        )


def _group_theses_by_symbol(
    theses: Iterable[WatchlistThesis],
) -> dict[str, tuple[WatchlistThesis, ...]]:
    grouped: dict[str, list[WatchlistThesis]] = {}
    for thesis in theses:
        grouped.setdefault(thesis.symbol, []).append(thesis)
    return {
        symbol: tuple(grouped[symbol])
        for symbol in sorted(grouped)
    }


def _group_signals_by_symbol(
    signals: Iterable[WatchlistSignal],
) -> dict[str, tuple[WatchlistSignal, ...]]:
    grouped: dict[str, list[WatchlistSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.symbol, []).append(signal)
    return {
        symbol: tuple(grouped[symbol])
        for symbol in sorted(grouped)
    }


def _build_summary(
    item: WatchlistItem,
    thesis: WatchlistThesis | None,
) -> str:
    if item.status is WatchlistStatus.ARCHIVED:
        return f"{item.symbol} is archived on the watchlist."
    elif item.reason:
        base = item.reason
    elif item.theme:
        base = f"Watchlist theme: {item.theme}."
    elif thesis is not None:
        base = thesis.thesis
    else:
        base = f"{item.symbol} remains on the watchlist for review."

    if item.theme and item.reason:
        return f"{_ensure_terminal_punctuation(base)} Theme: {item.theme}."
    return base


def _ensure_terminal_punctuation(value: str) -> str:
    """Return text with sentence-ending punctuation for appended clauses."""
    if value.endswith((".", "!", "?")):
        return value
    return f"{value}."


def _build_bullish_factors(
    thesis: WatchlistThesis | None,
    positive_signals: tuple[WatchlistSignal, ...],
) -> tuple[str, ...]:
    factors = list(thesis.key_drivers if thesis is not None else ())
    factors.extend(_format_signal(signal) for signal in positive_signals)
    return tuple(factors)


def _build_bearish_factors(
    thesis: WatchlistThesis | None,
    negative_signals: tuple[WatchlistSignal, ...],
) -> tuple[str, ...]:
    factors = list(thesis.risks if thesis is not None else ())
    factors.extend(_format_signal(signal) for signal in negative_signals)
    return tuple(factors)


def _format_signal(signal: WatchlistSignal) -> str:
    return f"{signal.signal_type}: {signal.summary}"


def _recommended_action(
    item: WatchlistItem,
    thesis: WatchlistThesis | None,
) -> str:
    if item.status is WatchlistStatus.ARCHIVED:
        return "archived"
    if thesis is None:
        return "review thesis"
    return "continue monitoring"


__all__ = ["WatchlistIntelligenceService"]
