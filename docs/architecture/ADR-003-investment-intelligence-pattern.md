# ADR 003: Investment Intelligence Layer Pattern

## Decision

ParakeetNest will use an Investment Intelligence Layer Pattern for derived
research views that sit between normalized data providers and the AI Committee.

Investment intelligence must be deterministic, provider-neutral, and testable
before it reaches Xixi, Dongdong, Yoyo, and the Chairman. A layer may classify,
calculate, score, summarize, or structure evidence, but it must do that work
behind explicit domain models, services, and context providers.

The standard flow is:

```text
Provider -> Service -> Classifier -> Snapshot -> Context Provider
  -> Prompt -> Committee
```

For derived layers, the provider step may be another normalized service rather
than an external source. The rule remains the same: raw provider payloads stop
before the committee path, and the committee receives rendered context.

## Context

ParakeetNest already has provider-backed layers for market data, news, SEC
filings, financial statements, and macro data. Epic 009 added a derived
Valuation Layer that calculates provider-neutral evidence from normalized
context. Epic 011 added an Economic Regime Layer that classifies macro
conditions from normalized macro snapshots.

Those layers expose a broader pattern. Some research evidence is not raw data;
it is investment intelligence produced from normalized facts. Economic regime,
sector rotation, portfolio risk, and strategy signals should be explainable and
repeatable before the committee reasons over them.

If these decisions were left to prompt text alone, the AI Committee would have
to parse provider payloads, infer classification rules, and decide how to handle
missing or invalid data at reasoning time. That would weaken testability and
make memory harder to trust.

The committee remembers before it reasons. That principle requires stable,
rendered context with clear source attribution, not ad hoc source parsing inside
the prompt.

## Pattern

An investment intelligence layer should follow this shape:

1. Provider or upstream service returns normalized facts.
2. Service owns orchestration and dependency boundaries.
3. Classifier, calculator, or engine performs deterministic reasoning.
4. Snapshot records the point-in-time intelligence output and evidence.
5. Context provider adapts the snapshot into `MeetingContext`.
6. Prompt renderer renders committee-readable context.
7. Committee consumes the rendered context alongside memory.

The AI Committee should consume rendered context rather than raw provider data
because rendered context is:

- provider-neutral;
- source-attributed;
- deterministic enough to test;
- compact enough for prompt assembly;
- consistent with memory records;
- safe from provider SDKs, payload quirks, and external exceptions.

The committee may debate the implications of the evidence. It should not own
the mechanics of provider parsing, classification thresholds, fallback behavior,
or context normalization.

## Relationship to Existing Principles

Clean Architecture remains the outer boundary rule. Vendor SDKs and concrete
provider details stay at the edge. Domain models, services, classifiers,
context providers, prompt rendering, and committee workflows depend inward on
stable abstractions.

Dependency Inversion applies at each boundary. Services depend on provider or
upstream service protocols. Context providers depend on service contracts.
Committee workflows depend on rendered context, not on concrete data sources.

The Provider Pattern still owns external source access. Providers normalize
payloads, hide SDK details, avoid hard-coded API keys, and translate
source-specific failures before data crosses into service layers.

The Service Pattern owns application orchestration. Services provide the public
entry point for retrieving or deriving intelligence, and they are the natural
home for caching, fallback, freshness policy, and later persistence.

The Context Provider Pattern adapts service outputs into `MeetingContext`.
Context providers decide whether a request is supported, preserve source
metadata, and prepare prompt-ready context without importing concrete providers.

The Memory-first AI Committee consumes context only after it has been assembled
and rendered. Memory, normalized evidence, and deterministic intelligence are
available before the committee reasons about action, confidence, horizon,
evidence, risks, and catalysts.

## Consequences

Investment intelligence becomes testable without live providers, network access,
or LLM calls. Rule sets, calculators, services, context providers, and rendering
can each have focused tests.

Derived outputs can explain their evidence. Snapshots capture the classification
or calculation result, confidence, source, observed date, indicators, notes, and
other metadata needed for committee reasoning.

The prompt surface stays stable even as providers or algorithms change. A live
provider, richer classifier, or new engine can be added behind the service
boundary without changing committee workflows.

There is additional up-front modeling work. Each intelligence layer needs
provider-neutral models, a service boundary, prompt-facing context models, and
tests. The tradeoff is intentional: ParakeetNest values repeatable research
evidence and safe dependency boundaries over opaque prompt-only reasoning.

## Applicability

Future Epics should use this pattern when they derive research intelligence
from normalized evidence:

- Sector Rotation: classify relative sector strength, macro sensitivity,
  leadership, and rotation risk behind deterministic snapshots.
- Risk Layer: convert market, macro, portfolio, and security evidence into
  testable risk signals before committee review.
- Portfolio Intelligence: summarize exposures, concentration, drawdown,
  liquidity, and factor posture through provider-neutral services.
- Strategy Engine: produce research-only strategy candidates, constraints, and
  rationale without automatic trading.

Automatic trading remains out of scope. Strategy and intelligence layers may
support research recommendations, but every recommendation must still include
action, confidence, horizon, evidence, risks, and catalysts.
