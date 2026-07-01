# Epic 34 - Daily Report v1 CLI

## Purpose

Epic 34 adds a simple local command that generates today's advisory daily
investment report as a Markdown/plain-text file.

The command reuses the existing daily report composer and research service. It
does not add scheduling, delivery, broker integrations, LLM provider calls, or a
new configuration system.

## Command Examples

Generate the default report:

```bash
python -m parakeetnest.cli.daily_report --tickers NVDA TSLA AAPL
```

Write to a custom path:

```bash
python -m parakeetnest.cli.daily_report \
  --tickers NVDA TSLA AAPL \
  --output reports/2026-07-01-daily-report.md
```

Include optional context inputs:

```bash
python -m parakeetnest.cli.daily_report \
  --tickers NVDA TSLA AAPL \
  --account-id main \
  --as-of-date 2026-07-01
```

## Output Path

If `--output` is not provided, the CLI writes to:

```text
reports/daily-report.md
```

The output directory is created automatically when it does not exist. After a
successful run, the command prints the report path.

## Advisory-Only Boundary

The daily report is advisory research only. It does not place trades, execute
orders, connect to brokerages, rebalance accounts, or make autonomous investment
decisions.

The human investor remains the final decision maker.

## Validation Checklist

- CLI writes a report file.
- Default output path works.
- Custom output path works.
- Ticker arguments are passed into the daily report composer.
- Report includes Market Summary, Portfolio Review, Watchlist Review, Dongdong,
  Xixi, and Youyou opinion sections, Committee Consensus, Confidence, Key Risks,
  Upcoming Catalysts, and Today's Suggested Actions.
- Missing or invalid tickers return a clear CLI error.
- No scheduler, email delivery, broker API, LLM provider call, autonomous
  trading, or complex config system is added.
- Full test suite passes.
