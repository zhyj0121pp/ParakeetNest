# Epic 24.3: Watchlist Intelligence Service

## Goal

Add a provider-neutral service that turns watchlist items, optional theses, and
optional signals into committee-ready `WatchlistInsight` objects.

## Scope

This epic adds:

- `WatchlistIntelligenceService`

The service supports:

- `build_insight(symbol, theses=(), signals=())`
- `build_all_insights(theses=(), signals=())`

## Behavior

`WatchlistIntelligenceService` depends on the `WatchlistRepository` abstraction
and reads existing watchlist items through that boundary. Missing symbols raise
`ValueError`.

Input theses and signals are grouped by normalized symbol before synthesis.
Insights are deterministic by symbol. Archived items can still be inspected
directly, but they receive an `archived` recommended action and are excluded
from `build_all_insights()` active output by default.

Insight summaries are derived from the watchlist item reason, item theme, or
thesis text. Bullish factors come from thesis key drivers and non-negative
signals. Bearish factors come from thesis risks and negative signals. Missing
thesis or signals become open questions so committee review can see what is not
yet documented.

Recommended actions remain conservative:

- `continue monitoring`
- `review thesis`
- `archived`

## Architecture Notes

The service performs deterministic synthesis only. It does not import or
implement market data, news, brokerage providers, LLM calls, committee/context
provider integration, persistence, automatic trading, or CLI behavior.

This epic extends the Watchlist Intelligence line without adding a new ADR.

## Validation Checklist

- [x] Watchlist intelligence service added.
- [x] Service depends on `WatchlistRepository`.
- [x] Missing item raises `ValueError`.
- [x] Archived items do not produce active `build_all_insights()` output.
- [x] Thesis inputs contribute summary, bullish factors, and bearish factors.
- [x] Signal inputs contribute bullish and bearish factors.
- [x] Missing thesis or signals create open questions.
- [x] All-insight output is deterministic by symbol.
- [x] No provider, LLM, context-provider, persistence, automatic trading, or CLI
      integration added.
