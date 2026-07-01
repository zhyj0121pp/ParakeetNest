# Epic 036: Daily Report Context Wiring

## Purpose

Wire the daily report CLI to existing ParakeetNest context services so the
report uses factual watchlist and investment intelligence context before the
committee judgment layer reasons over it.

The flow remains:

```text
Facts / Context -> Committee Judgment -> Daily Report
```

## CLI Examples

Generate a report from the configured watchlist seed:

```bash
python -m parakeetnest.cli.daily_report \
  --watchlist-seed data/watchlist.json
```

Generate a report from a seed configured by environment:

```bash
PARAKEETNEST_WATCHLIST_SEED_PATH=data/watchlist.json \
python -m parakeetnest.cli.daily_report
```

Override the default universe for debugging or one-off research:

```bash
python -m parakeetnest.cli.daily_report --tickers NVDA TSLA AAPL
```

Use an isolated local database path:

```bash
python -m parakeetnest.cli.daily_report \
  --database data/parakeetnest.sqlite3 \
  --watchlist-seed data/watchlist.json
```

## Default Watchlist Behavior

When `--tickers` is omitted, the CLI builds the normal application container and
uses `watchlist_intelligence_service.build_all_insights()` as the default report
universe.

If no explicit tickers are provided and no configured seed produces active
watchlist symbols, the CLI fails clearly:

```text
No tickers provided and no watchlist seed is configured.
```

## Explicit Ticker Override

`--tickers` remains an override/debug option. When present, those symbols are the
report universe even if a watchlist seed is configured.

## Wired Now

- Daily report composition uses the app's `WatchlistIntelligenceService`.
- Daily report composition uses the app's investment intelligence context
  service when available.
- Seeded watchlist symbols can drive the default report universe.
- Watchlist summaries, factors, open questions, and source evidence appear in
  factual ticker context.

## Still Disconnected

- Portfolio service remains optional and is not auto-wired by this epic.
- Broker integrations are not introduced.
- LLM provider calls are not introduced.
- Trading or portfolio execution is not introduced.

## Advisory-Only Boundary

The daily report remains advisory research. It may suggest actions for a human
investor to review, but it does not make autonomous investment decisions, place
orders, rebalance accounts, or connect to brokerage systems.

## Validation Checklist

- [x] CLI can run without `--tickers` when a watchlist seed exists.
- [x] CLI still supports explicit `--tickers` override.
- [x] CLI fails clearly when neither tickers nor watchlist seed exists.
- [x] Watchlist service is passed into daily report generation.
- [x] Generated report includes watchlist factual context.
- [x] Report no longer says `No watchlist service connected.` when watchlist is
  wired.
- [x] Existing explicit-ticker CLI behavior still works.
- [x] No broker, trading, or LLM provider logic is introduced.
