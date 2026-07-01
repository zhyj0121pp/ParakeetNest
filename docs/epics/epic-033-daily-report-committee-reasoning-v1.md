# Epic 33: Daily Report Committee Reasoning v1

## Purpose

Epic 33 turns persona prompt artifacts into deterministic committee opinions
that improve the daily investment report the user reads.

The daily report now gives Dongdong, Xixi, and Youyou clear advisory opinions
with stance, reasoning, evidence, concern, and suggested action. The goal is to
make the report more practical without adding LLM provider calls, debate memory,
broker integration, or autonomous decisioning.

## Simplified Product Direction

ParakeetNest is focused on a practical daily investment report with investment
advice. The committee should help the human investor decide what deserves
attention today.

Implementation should remain simple:

- Use existing portfolio, watchlist, and intelligence context.
- Use permanent persona fields to shape each committee member's lens.
- Prefer deterministic reasoning that is easy to test.
- Avoid new abstractions unless they directly improve the report.

## Report Impact

Each committee section renders in a readable daily-report format:

- Stance: bullish, neutral, or cautious.
- Reasoning: a concise persona-specific summary.
- Evidence: report inputs considered by that persona.
- Concern: the most important gap or risk.
- Suggested Action: advisory next step for the human investor.

Persona emphasis:

- Dongdong emphasizes upside, innovation, catalysts, and long-term growth.
- Xixi emphasizes fundamentals, valuation, earnings quality, and execution.
- Youyou emphasizes downside, liquidity, macro, and capital preservation.

The final report still includes Market Summary, Portfolio Review, Watchlist
Review, all three committee opinions, Committee Consensus, Confidence, Key
Risks, Upcoming Catalysts, and Today's Suggested Actions.

## Advisory-Only Boundary

The report is advisory research only. It does not place trades, execute orders,
connect to brokerages, rebalance accounts, or make autonomous investment
decisions.

A human investor remains the final decision maker.

## Validation Checklist

- All three committee opinions are generated.
- Each opinion includes stance, reasoning, evidence, concern, and suggested
  action.
- Report rendering uses the new committee opinion format.
- Report output remains advisory-only.
- No broker or trading execution logic is introduced.
- Full test suite passes.
