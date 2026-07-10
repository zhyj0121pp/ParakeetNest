# Epic 32 - Persona-Driven Prompt Generation

## Purpose

Epic 32 turns the permanent investment committee personas from Epic 31 into
provider-neutral prompt inputs for daily committee reasoning. Dongdong, Xixi,
and Yoyo now receive prompt context shaped by their stable persona
definitions before committee opinions are assembled for the daily investment
report.

The goal is better committee-specific reasoning without introducing an LLM
provider, broker integration, automatic trading, or autonomous decisions.

## Architecture

Prompt generation lives in `src/parakeetnest/committee/prompting.py`.

The module defines only immutable prompt models and a deterministic prompt
builder:

- `CommitteePromptContext`
- `CommitteePersonaPrompt`
- `CommitteePromptBuilder`
- `PersonaDrivenCommitteePromptBuilder`

The research service builds one prompt context for each permanent committee
member in daily report order: Dongdong, Xixi, Yoyo. It then uses the prompt
builder to create internal prompt artifacts and derives clean
`ResearchCommitteeOpinion` records from those prompt contexts.

Raw prompt text is not rendered in the daily report. The report remains readable
and advisory, while the prompt layer prepares the system for future committee
reasoning.

## Prompt Model

Each `CommitteePromptContext` includes:

- persona
- tickers
- market summary
- portfolio review
- watchlist review
- ticker summaries
- evidence notes
- key risks
- upcoming catalysts
- advisory-only disclaimer

Each generated prompt includes:

- persona display name
- role title
- responsibility
- default viewpoint
- risk posture
- evidence requirements
- decision biases to avoid
- relevant ticker and report context
- advisory-only boundary
- required output expectations

The prompt builder uses persona fields directly instead of branching on persona
IDs such as `dongdong`, `xixi`, or `yoyo`.

## Future LLM Readiness

This epic prepares ParakeetNest for future LLM-backed committee reasoning by
creating a stable provider-neutral prompt boundary. A future adapter can consume
`CommitteePersonaPrompt` objects without changing persona definitions, research
models, report rendering, or portfolio/watchlist data sources.

No OpenAI, Anthropic, Yahoo, broker, or execution-specific code is introduced by
this epic.

## Advisory-Only Boundary

Prompt generation is advisory research only. It does not execute trades, route
orders, connect to brokers, store API keys, or make autonomous decisions.

Daily reports may include suggested actions, confidence, horizon, evidence,
risks, and catalysts. The human investor remains the final decision maker.

## Daily Report Impact

Committee opinions continue to render as concise daily-report sections:

- Dongdong's Opinion
- Xixi's Opinion
- Yoyo's Opinion

The generated prompts remain internal generation input. They improve consistency
and future extensibility without bloating the final report with raw prompt text.

## Validation Checklist

- Prompt builder creates exactly three prompts.
- Prompt order is Dongdong, Xixi, Yoyo.
- Each prompt contains persona identity and role.
- Each prompt contains the advisory-only disclaimer.
- Each prompt contains relevant ticker context.
- Prompt output comes from persona fields rather than hardcoded persona-ID
  branches.
- Daily report output remains stable and readable.
- Recommendations still include action, confidence, horizon, evidence, risks,
  and catalysts.
- No LLM provider calls are introduced.
- No broker integration, order execution, automatic trading, or autonomous
  investment decisioning is introduced.
