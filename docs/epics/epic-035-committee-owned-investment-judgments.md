# Epic 035: Committee-Owned Investment Judgments

## Problem

The daily report path previously let research output include recommendation
actions and confidence before the committee reasoned. That caused committee
opinions to explain a pre-existing recommendation instead of owning the
investment judgment.

## Simplified Architecture

Facts and context flow into factual ticker context first. The committee then
reviews that context and produces opinions and consensus.

Research owns:

- ticker summaries
- bull and bear evidence
- factual risk signals
- factual catalyst signals
- findings
- source summaries
- evidence notes

Committee output owns:

- each persona stance
- reasoning summary
- evidence considered
- key concern
- suggested action
- final action
- confidence
- horizon
- rationale
- final risk posture
- today's suggested actions

## Facts vs Judgments

Facts describe what connected services know. Judgments decide what the
committee thinks a human investor should consider. Research context can say that
a ticker has export-control risk or an upcoming earnings catalyst. Only the
committee can turn that context into watch, hold, reduce, sell, buy, confidence,
consensus, or suggested action language.

## Deleted Obsolete Code

The research-specific recommendation model, action enum, confidence enum, and
renderer block for pre-committee recommendations were removed from the research
report path. The daily CLI still generates `reports/daily-report.md`.

## Report Impact

The daily report now renders market summary, portfolio review, watchlist review,
factual ticker context, Dongdong's opinion, Xixi's opinion, Youyou's opinion,
committee consensus, confidence, key risks, upcoming catalysts, today's
suggested actions, and evidence notes.

Missing provider notes are aggregated at report level, avoiding repeated
per-ticker noise.

## Advisory-Only Boundary

This epic adds no scheduling, delivery, broker integration, order placement,
automatic trading, LLM provider calls, or autonomous investment decisions. The
committee output is advisory. The human investor makes the final decision.

## Validation Checklist

- [x] Research service emits factual ticker context without recommendation
      action or final confidence.
- [x] Committee opinions include stance, reasoning, evidence, concern, and
      suggested action.
- [x] Committee consensus owns final action, confidence, horizon, rationale,
      final risk posture, and today's suggested actions.
- [x] Report no longer renders a separate pre-committee Recommendations
      section.
- [x] Daily report CLI writes an interactive HTML report file.
- [x] Evidence notes avoid repeated missing-service messages per ticker.
- [x] Advisory-only boundary remains intact.
