# Architecture Milestone Review v1.1

Date: 2026-06-30

Status: Completed review after Epic 12.

Scope: Architecture and documentation review only. No runtime behavior,
feature implementation, or production code refactoring is included in this
milestone review.

## Scope

This review evaluates whether the Phase II Investment Intelligence Layer is
consistent, reusable, and ready to support Epic 13: Risk Layer.

Reviewed layers:

- Epic 009: Valuation Layer
- Epic 011: Economic Regime Layer
- Epic 012: Sector Rotation Layer

Reviewed integration points:

- `MeetingContext` and prompt-facing context snapshots
- `ContextProviderRegistry` and `ContextService`
- `MeetingContextPromptRenderer`
- application bootstrap in `src/parakeetnest/app.py`
- epic documentation, documentation indexes, and ADR-003

Out of scope:

- implementing Epic 13
- refactoring the Context Layer
- refactoring application bootstrap
- adding new runtime behavior
- adding automatic trading

## Current Architecture State

ParakeetNest v1.1 extends the v1.0 evidence pipeline with repeatable investment
intelligence layers. The current architecture separates normalized facts,
deterministic interpretation, context assembly, prompt rendering, and committee
reasoning.

The effective investment intelligence flow is:

```text
Provider or upstream normalized facts
  -> Service
  -> Calculator or classifier
  -> Snapshot
  -> Context provider
  -> MeetingContext
  -> MeetingContextPromptRenderer
  -> AI Committee
```

The committee continues to receive provider-neutral rendered context rather
than raw vendor payloads, concrete provider clients, or classifier internals.
This preserves the project principle that the committee remembers before it
reasons.

Overall architecture status: **v1.1 milestone ready to freeze with deferred,
non-blocking improvements.**

## Investment Intelligence Layer Review

Epic 009, Epic 011, and Epic 012 are directionally consistent with ADR-003's
Investment Intelligence Layer Pattern.

### Epic 009: Valuation Layer

The Valuation Layer follows the derived-intelligence pattern inside its package:

```text
normalized market and financial context
  -> ValuationInputBuilder
  -> ValuationService
  -> ValuationCalculator
  -> ValuationSnapshot
  -> ValuationContextProvider
  -> MeetingContext.valuation
  -> Prompt Renderer
```

Strengths:

- valuation inputs are built from normalized context snapshots;
- valuation calculations are deterministic and network-free;
- calculator behavior is hidden behind `ValuationService`;
- valuation context is provider-neutral and prompt-rendered;
- tests cover models, input building, calculation, service delegation, context
  provider behavior, and rendering.

Deferred caveat:

- `ValuationContextProvider` is implemented and tested, but application
  bootstrap does not register it by default because it currently expects market
  and financial statement snapshots to be injected. This is an integration
  sequencing issue rather than a pattern violation.

### Epic 011: Economic Regime Layer

The Economic Regime Layer follows the pattern end to end:

```text
MacroDataProvider
  -> MacroDataService
  -> EconomicRegimeService
  -> EconomicRegimeClassifier
  -> EconomicRegimeSnapshot
  -> EconomicRegimeContextProvider
  -> MeetingContext.economic_regime
  -> Prompt Renderer
```

Strengths:

- classification uses normalized macro snapshots;
- classifier rules are deterministic, reviewable, and testable;
- `EconomicRegimeService` owns orchestration and fallback behavior;
- context output is provider-neutral;
- bootstrap registers only the service-backed context provider, not classifier
  internals.

### Epic 012: Sector Rotation Layer

The Sector Rotation Layer follows the pattern through a provider-backed
service:

```text
SectorRotationProvider
  -> SectorRotationService
  -> SectorRotationCalculator
  -> SectorRotationSnapshot
  -> SectorRotationContextProvider
  -> MeetingContext.sector_rotation
  -> Prompt Renderer
```

Strengths:

- sector rotation snapshots use provider-neutral domain models;
- relative strength and momentum calculation remain behind
  `SectorRotationService`;
- context output is deterministic and prompt-facing;
- application bootstrap registers the context provider through the registry;
- tests cover models, calculator behavior, service behavior, context provider
  behavior, prompt rendering, and bootstrap registration.

## Context Layer Review

`MeetingContext` has grown in a controlled way. It now contains dedicated
optional sections for `valuation`, `economic_regime`, and `sector_rotation`.
Each section uses provider-neutral context models rather than service objects,
provider instances, or raw payload dictionaries.

`ContextProviderRegistry` remains simple and maintainable. It registers stable
provider IDs, supports enable/disable configuration, and resolves enabled
providers before `ContextService` is created.

`ContextService` still provides deterministic assembly:

- providers execute in configured order;
- each provider contributes a partial `MeetingContext`;
- first-provider-wins section merging prevents accidental overwrites;
- source metadata, warnings, and provider metadata notes are merged
  deterministically.

Prompt rendering is consistent. `MeetingContextPromptRenderer` renders
dedicated sections for valuation, economic regime, and sector rotation. The
renderer formats context that has already been prepared; it does not call
services, calculate metrics, classify regimes, or query providers.

Provider-neutral context snapshots are intact. Context providers depend on
service contracts or protocols and remain deterministic enough to test without
network access or LLM calls.

Observed context-layer concern:

- `ContextRequest.include_macro` is reused to control macro context, economic
  regime, and sector rotation. This is acceptable for v1.1, but it is becoming
  semantically broad. Future intelligence layers may need more specific include
  flags or an explicit requested-context mechanism.

## Bootstrap Review

`src/parakeetnest/app.py` remains the central composition root. It creates
services, registers context providers, applies provider configuration, and then
constructs `ContextService`.

Bootstrap strengths:

- concrete provider selection remains at the application edge;
- services are created before context providers;
- economic regime and sector rotation register service-backed context
  providers;
- calculators and classifiers are not registered directly in
  `ContextProviderRegistry`;
- mock providers remain deterministic defaults for local development and
  tests;
- SEC EDGAR configuration still requires explicit user-agent configuration.

Bootstrap risks:

- `app.py` is growing as each layer adds service creation and provider
  registration;
- valuation is not registered by default yet because derived context currently
  cannot consume previously assembled market and financial statement sections
  during the same context build;
- repeated service factory and context provider registration code may become
  boilerplate as Epic 13 and later layers arrive.

These are maintainability risks, not blockers for freezing v1.1.

## Documentation Review

Epic documentation is mostly consistent:

- Epic 009 documents valuation as a derived evidence layer and calls out the
  bootstrap registration limitation;
- Epic 011 documents the economic regime service, classifier, context provider,
  prompt rendering, and tests;
- Epic 012 documents sector rotation foundation, calculation, context
  integration, prompt rendering, and bootstrap registration.

ADR-003 still adequately covers the current pattern. It describes deterministic
investment intelligence, service boundaries, calculator/classifier internals,
snapshots, context providers, prompt rendering, and committee consumption. No
new ADR is required for v1.1.

Documentation gaps found during review:

- the top-level documentation index did not list Epic 012 before this review;
- the README documentation list did not include the v1.1 review before this
  review;
- roadmap language still describes the Phase II epic list as directional and
  partly stale. This is non-blocking because the epic index is the source of
  delivery truth, but the roadmap should be refreshed after the v1.1 freeze.

## Risks and Deferred Improvements

Non-blocking risks:

- `app.py` may become harder to scan as more intelligence layers are added.
- Context provider boilerplate is repeated across intelligence layers.
- `include_macro` now gates macro, economic regime, and sector rotation.
- Confidence values are not standardized across all intelligence layers.
  Valuation, economic regime, and future risk signals should converge on
  common confidence semantics or document layer-specific meanings.
- Prompt rendering may become large as more intelligence sections are added.
- Valuation context is not yet registered in application bootstrap by default.
- Derived context providers may eventually need a multi-pass context assembly
  model so later providers can consume earlier provider-neutral context
  sections.
- Intelligence snapshots are not yet persisted as first-class SQLite records.

Recommended fixes now:

- Add this v1.1 milestone review to the documentation index.
- Add Epic 012 to the top-level documentation index.
- Keep ADR-003 as the governing architecture decision.
- Freeze v1.1 without introducing runtime changes.

Recommended deferrals:

- Defer app bootstrap decomposition until Epic 13 adds enough pressure to show
  the right module boundary.
- Defer a generic derived-context pipeline until valuation or risk needs to
  consume already assembled context in production bootstrap.
- Defer confidence standardization until Epic 13 defines risk confidence and
  exposes the cross-layer comparison problem more clearly.
- Defer prompt-renderer decomposition until prompt size or readability becomes
  a concrete problem.
- Defer intelligence snapshot persistence until there is a clear retrieval,
  audit, or memory requirement.

## Decision

ParakeetNest v1.1 architecture can be frozen.

Rationale:

- the Investment Intelligence Layer pattern is now demonstrated across
  valuation, economic regime, and sector rotation;
- deterministic calculators and classifiers remain behind service boundaries;
- provider-neutral snapshots reach the Context Layer before prompt rendering;
- committee workflows consume rendered context rather than implementation
  details;
- bootstrap remains maintainable enough for the next epic;
- no major architecture blocker was found for Epic 13.

Freeze caveat:

- v1.1 freezes the current architecture pattern, not every deferred integration
  improvement. In particular, default valuation bootstrap registration remains
  deferred until derived providers can safely consume prior normalized context
  sections.

## Next Recommended Epic

The next recommended epic is **Epic 13: Risk Layer**.

Epic 13 should follow ADR-003 and the v1.1 pattern:

```text
upstream provider-neutral evidence
  -> RiskService
  -> Risk classifier, calculator, or scoring engine
  -> RiskSnapshot
  -> RiskContextProvider
  -> MeetingContext.risk
  -> Prompt Renderer
  -> AI Committee
```

The Risk Layer should remain research-only. It should produce evidence,
signals, confidence, risks, and catalysts for committee reasoning, but it must
not implement automatic trading.
