# Epic 37: Morning and Evening Report Modes

## Purpose

Epic 37 turns the generic daily investment report into two explicit advisory
report modes:

- Morning Brief: pre-market investment advice.
- Evening Review: post-market review and next-day preparation.

The architecture remains:

Facts / Context -> Committee Judgment -> Report

Both modes reuse the existing watchlist facts, investment intelligence context,
factual ticker context, and committee judgment service. This epic does not add
new data providers, scheduling, email delivery, broker integration, automated
trading, or LLM provider calls.

## Morning Report Goal

The Morning Brief answers:

What should I focus on before market open?

It emphasizes actions, focus areas, catalysts, risks, and committee judgment
before the trading day begins.

## Evening Report Goal

The Evening Review answers:

What changed today, and what should I prepare for tomorrow?

It emphasizes recap, changes, lessons, risk review, and next-day preparation
after the market closes.

## CLI Examples

```bash
python -m parakeetnest.cli.daily_report --mode morning --watchlist-seed data/watchlist.json
```

```bash
python -m parakeetnest.cli.daily_report --mode evening --watchlist-seed data/watchlist.json
```

Explicit tickers remain supported as an override and debug path:

```bash
python -m parakeetnest.cli.daily_report --mode morning --tickers NVDA AAPL
```

The default mode is morning. The default output path remains
`reports/daily-report.md` unless `--output` is provided.

## Morning Report Structure

- Header
- Market Setup
- Portfolio Watch
- Watchlist Focus
- Today’s Focus
- Dongdong’s Opportunity View
- Xixi’s Fundamental View
- Yoyo’s Risk View
- Committee Consensus
- Confidence
- Key Risks
- Upcoming Catalysts
- Today's Suggested Actions
- Evidence Notes

## Evening Report Structure

- Header
- Market Recap
- Portfolio Review
- Watchlist Review
- What Changed
- Dongdong’s Opportunity Review
- Xixi’s Fundamental Review
- Yoyo’s Risk Review
- Committee Consensus
- Confidence
- Key Risks
- Tomorrow’s Focus
- Suggested Follow-ups
- Evidence Notes

## Advisory-Only Boundary

- No automated trading.
- No broker integration.
- No order placement.
- No email delivery changes.
- No scheduler changes.
- No LLM provider calls.
- Human investor makes the final decision.

Every recommendation remains advisory and must include action, confidence,
horizon, evidence, risks, and catalysts through the existing committee judgment
and report rendering contract.

## Validation Checklist

- Default CLI mode is morning.
- CLI accepts `--mode morning`.
- CLI accepts `--mode evening`.
- Invalid mode returns a clear parser error.
- Morning title is `Morning Investment Brief`.
- Evening title is `Evening Investment Review`.
- Morning report includes `Today’s Focus`.
- Evening report includes `What Changed` and `Tomorrow’s Focus`.
- Explicit ticker behavior still works.
- Watchlist seed behavior still works.
- No broker, trading, scheduler, delivery, or LLM provider logic is introduced.
- Full test suite passes.
