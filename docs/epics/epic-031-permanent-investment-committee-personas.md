# Epic 31 - Permanent Investment Committee Personas

## Purpose

Epic 31 makes Dongdong, Xixi, and Yoyo stable domain concepts for the daily
investment report. The report should not depend on loose hardcoded text for
committee identity; it should derive committee sections from durable persona
definitions.

The daily investment committee is:

- Dongdong, Chief Growth Officer
- Xixi, Chief Investment Analyst
- Yoyo, Chief Risk Officer

## Architecture

Permanent personas live under `src/parakeetnest/committee/personas.py`.

The committee persona module is provider-neutral. It defines immutable domain
models and an in-memory registry/service only. It does not call LLM providers,
market data providers, broker APIs, persistence adapters, or external services.

The research service depends on a small committee-service protocol and defaults
to `PermanentCommitteeService`. During report assembly, the service converts the
daily committee into provider-neutral `ResearchCommitteeOpinion` records. The
plain-text renderer then renders daily report sections from those records.

This preserves the existing Clean Architecture shape:

- committee domain owns permanent persona identity and responsibility
- research service composes report data from provider-neutral abstractions
- renderer formats report data only
- composer orchestrates research generation and rendering only

## Domain Model

The persona model includes:

- `CommitteePersona`
- `CommitteeRole`
- `CommitteeOpinionStyle`
- `CommitteeMemberProfile`
- `PermanentCommitteeService`

Each persona defines:

- stable `id`
- `display_name`
- `role_title`
- `responsibility`
- `default_viewpoint`
- `risk_posture`
- `evidence_requirements`
- `writing_style`
- `decision_biases_to_avoid`

The permanent daily order is `dongdong`, `xixi`, `yoyo`.

## Why Personas Are Stable Domain Concepts

The committee members are part of ParakeetNest's investment process, not
temporary prompt text. Stable personas make daily reports consistent over time,
allow memory and future committee behavior to attach to durable identities, and
make it clear which lens produced each section of the advisory report.

Personas remain separate from runtime agent profiles. Agent profiles describe
execution metadata such as prompt sources and output contracts. Permanent
personas describe committee identity, responsibility, viewpoint, risk posture,
and reporting style.

## Advisory-Only Boundary

This epic does not introduce automatic trading, broker integration, order
routing, account execution, API keys, or provider-specific logic.

The daily report remains an advisory research artifact. It may include suggested
actions, confidence, evidence, risks, catalysts, and committee opinions, but the
human user remains the final decision maker.

## Daily Report Impact

The daily investment report includes:

- Market Summary
- Portfolio Review
- Watchlist Review
- Dongdong's Opinion
- Xixi's Opinion
- Yoyo's Opinion
- Committee Consensus
- Confidence
- Key Risks
- Upcoming Catalysts
- Today's Suggested Actions

Committee opinion sections use the permanent persona display names and role
titles from the persona registry.

## Validation Checklist

- All three permanent personas exist.
- Daily committee order is stable: `dongdong`, `xixi`, `yoyo`.
- Persona IDs are unique.
- Each persona has a role, responsibility, risk posture, evidence requirements,
  writing style, and decision biases to avoid.
- The registry rejects duplicate persona IDs.
- The daily report composer renders persona display names and roles correctly.
- Existing recommendation requirements remain intact: action, confidence,
  horizon, evidence, risks, and catalysts.
- No autonomous trading, broker integration, provider-specific LLM logic, or
  brokerage portfolio integration is introduced.
