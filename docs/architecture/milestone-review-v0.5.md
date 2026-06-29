# Architecture Milestone Review v0.5

Date: 2026-06-29

Status: Completed review after Epic 5, before Epic 6.

Scope: Architecture review only. No feature, refactoring, or behavior changes are
included in this milestone review.

## Executive Summary

ParakeetNest v0.5 has a strong architecture for a v1 AI investment research
platform. The system has evolved from a deterministic foundation into a layered,
provider-aware application with SQLite persistence, memory-first committee
execution, a context assembly pipeline, an LLM abstraction, and a market data
provider boundary with Yahoo Finance behind a registry.

The most important architectural success is that the committee remains insulated
from raw provider APIs. Market data enters through provider-neutral models,
passes through services and context, and reaches agents as rendered meeting
context. This directly supports the project rule that the committee remembers
before it reasons.

The main v0.5 risk is duplication across older normalized snapshots, newer
context snapshots, and newer market data models. This is manageable today, but
Epic 6 will introduce external news content, which is less structured, more
source-sensitive, and more legally and reputationally sensitive than market
quotes. The News Layer should reuse the provider and registry pattern, but it
also needs explicit source attribution, deduplication, freshness, text-length,
and error semantics from the start.

Overall architecture score: **8.4 / 10**

Readiness for Epic 6: **Ready with guardrails**

## Review Areas

### 1. Package Organization

The current package structure is coherent and mostly aligned with the documented
architecture:

- `config`, `logging`, `exceptions`, and `runtime` provide foundation concerns.
- `domain` and `models` hold stable provider-neutral data and recommendation
  models.
- `database` owns SQLite setup, ORM models, repositories, and persistence
  adapters.
- `memory` owns investment memory and knowledge recall concepts.
- `context` owns pre-reasoning context assembly and rendering.
- `market_data` owns quote and price-history provider boundaries.
- `llm` owns model-provider abstraction, prompts, parsing, and schemas.
- `committee` owns agents, prompts, runtime execution, and orchestration.
- `services` owns application services and workflow entry points.
- `decision`, `reports`, `scheduler`, and `analyzers` remain available for
  future specialization.

The organization is strongest in the newer `context` and `market_data` packages,
where protocols, registries, service adapters, models, and tests are clearly
separated.

The main concern is that `services` now contains both older mock data services
and higher-level application services such as `MeetingService`. That is still
acceptable, but Phase 2 may benefit from clearer naming between data collection
services and application workflow services.

### 2. Layer Boundaries

Layer boundaries are generally strong:

- The committee does not import Yahoo Finance or other provider SDKs.
- `MeetingService` receives market facts through `ContextService`, not through
  direct market data dependencies.
- `MarketDataService` depends on the `MarketDataProvider` protocol.
- `ContextService` depends on the `ContextProvider` protocol.
- The application bootstrap wires concrete implementations in one place.
- Boundary tests enforce several important import rules.

Known pressure points:

- `CommitteeMeetingOrchestrator` depends directly on
  `CommitteeMeetingRepository`, which couples committee orchestration to SQLite
  persistence. This is workable for v0.5, but the documented direction favors
  protocols at workflow boundaries.
- Context models duplicate some older `domain` snapshot concepts. This can be
  intentional if context is a presentation-facing aggregate, but the distinction
  should remain explicit as new data families arrive.

### 3. Dependency Direction

Dependency direction is mostly correct:

```text
configuration/bootstrap
  -> provider registries
  -> provider-neutral services
  -> context assembly
  -> meeting service
  -> committee runtime
```

The strongest example is the Market Data Layer:

```text
AppConfig
  -> MarketDataProviderRegistry
  -> MarketDataProvider
  -> MarketDataService
  -> MarketContextProvider
  -> ContextService
  -> MeetingService
  -> CommitteeMeetingOrchestrator
```

This is the right shape for future provider-backed layers.

The remaining architectural gap is that not every boundary uses protocols yet.
The market data and context layers do; persistence and LLM selection are still
more concrete in application bootstrap and meeting orchestration.

### 4. Public APIs

The public APIs are small and improving:

- `parakeetnest.market_data` exports provider-neutral models, errors, provider
  protocol, registry, service, and concrete providers intentionally.
- `MarketDataService` has a narrow public API for snapshots and price history.
- `ContextProvider` and `ContextProviderResult` define a clear provider
  contribution contract.
- `MeetingService.run(question, ticker)` gives the CLI and application a simple
  entry point.

Risks:

- Some public exports expose concrete providers directly. This is useful for
  tests and explicit construction, but callers should still prefer registries
  and services.
- `MeetingService.run()` currently accepts one ticker. Epic 6 can work with
  this, but multi-symbol news and portfolio workflows will eventually pressure
  this interface.
- `ContextProviderResult.errors` are plain strings. This keeps the context layer
  simple, but provider-rich layers may need typed, provider-neutral errors.

### 5. Naming Consistency

Naming is mostly consistent and readable:

- Provider IDs such as `mock`, `yahoo`, `market_data`, and `mock_news` are clear.
- Committee role names match the product language.
- Market data names are provider-neutral.
- Context names clearly indicate request, provider result, metadata, and final
  meeting context.

Inconsistencies to watch:

- The context architecture document still lists `mock_market`, while bootstrap
  registers the market context provider as `market_data`.
- The project uses both `ticker` and `symbol`. Market Data Layer models use
  `Symbol`; meeting and database records often use `ticker`. A future naming
  pass should define when each term is appropriate.
- `domain.MarketSnapshot`, `context.MarketSnapshot`, and
  `market_data.MarketDataSnapshot` are all valid in their layers but easy to
  confuse.

### 6. Domain Models

The domain model direction is sound:

- Core recommendation models enforce action, confidence, horizon, evidence,
  risks, and catalysts.
- Market data models are immutable, provider-neutral, and normalized.
- Context models aggregate typed sections before rendering prompts.
- Database models remain persistence-specific and are not leaking into market
  data providers.

Technical debt:

- The older `domain` snapshots and newer `context` snapshots overlap. This may
  be the correct split between collected facts and assembled prompt context, but
  the difference should be documented more explicitly before more layers are
  added.
- There is not yet a shared source/citation model. Epic 6 should introduce one
  for news rather than spreading `source`, `url`, `published_at`, and summary
  semantics across unrelated classes.
- Investment thesis memory and committee meeting persistence are conceptually
  separate, but the current app still has a mostly SQLite-centered flow.

### 7. Provider / Registry Pattern

The provider and registry pattern is the strongest architecture pattern in
v0.5.

Strengths:

- `MarketDataProvider` is small and testable.
- `MarketDataProviderRegistry` centralizes provider selection.
- Unknown provider IDs fail early with clear configuration errors.
- The default provider is deterministic and network-free.
- Yahoo Finance code is isolated to the Yahoo adapter.
- Tests verify mapping, retry behavior, error translation, and dependency
  isolation without live network calls.

Recommendations for Epic 6:

- Create a dedicated News Layer rather than expanding mock context providers
  directly.
- Use the same pattern: `NewsProvider`, `NewsProviderRegistry`, `NewsService`,
  provider-neutral models, provider-neutral errors, and a context adapter.
- Keep summarization out of raw news providers. Providers should fetch and
  normalize source material; LLM interpretation belongs later in committee or
  report workflows.

### 8. Configuration

Configuration is clean for v0.5:

- `AppConfig` is small and test-friendly.
- `MarketDataConfig` isolates provider selection.
- Environment settings avoid hard-coded API keys.
- Secret values use `SecretStr`.
- Context providers can be enabled or disabled by ID.

Risks:

- Context provider unknown IDs currently raise `KeyError`; market data provider
  unknown IDs raise `ConfigurationError`. The public error style should be
  aligned before configuration grows.
- Provider-specific configuration is minimal. Epic 6 may need API keys, fetch
  limits, timeouts, allowed sources, and freshness windows.
- Live-provider configuration should remain opt-in. The mock path should stay
  default and deterministic.

### 9. Error Hierarchy

The project has a general exception hierarchy and a stronger market-data-specific
hierarchy.

Strengths:

- `MarketDataError` subclasses express provider-independent failures.
- Retryability is modeled on provider availability errors.
- Yahoo-specific exceptions are translated before leaving the provider boundary.
- `ConfigurationError` exists for invalid application setup.

Debt:

- Market data errors do not inherit from `ParakeetNestError`. This is not
  breaking today, but a consistent root exception would simplify broad
  application-level handling.
- Context provider errors are represented as strings in successful
  `ContextProviderResult` objects. That is simple, but may become too weak for
  source-sensitive news ingestion.
- Provider error classes should eventually include source, operation, symbol or
  query, retryability, and safe user-facing message metadata consistently.

### 10. Testing Strategy

The testing strategy is a major strength.

Current coverage includes:

- database setup and repositories;
- knowledge base behavior;
- committee engine, meetings, orchestrator, and agent runtime;
- LLM layer abstractions and schemas;
- context provider registry, provider behavior, context merging, and rendering;
- market data models, provider protocol, registry, service, mock provider, Yahoo
  provider, and error mapping;
- CLI and app bootstrap;
- architecture boundary tests.

The most important test strategy choice is that live network calls are not part
of the default suite. This should remain true for Epic 6.

Recommended additions for Phase 2:

- contract tests reusable across all provider types;
- fixture-based provider tests for news payload normalization;
- tests for source attribution and citation preservation;
- tests that prevent LLM summarization from entering raw provider layers;
- architecture tests for new provider SDK isolation.

### 11. Documentation Quality

Documentation quality is strong for the current maturity level:

- `docs/design.md` captures mission, committee roles, and guiding principles.
- `docs/dependency-boundaries.md` documents import expectations.
- `docs/rfc/001-architecture-freeze.md` explains the memory-first architecture.
- `docs/architecture/context-layer.md` documents context assembly behavior.
- `docs/architecture/market-data-layer.md` documents provider abstraction,
  registry flow, error hierarchy, retry policy, and future providers.
- Epic documents preserve implementation intent and completion criteria.

Needed improvements:

- Update context provider IDs in documentation to match bootstrap.
- Add a short architecture index that distinguishes `domain`, `context`, and
  provider-specific model families.
- Keep ADRs current as Epic 6 introduces more external data and text content.
- Add diagrams for end-to-end meeting execution after context and market data
  additions.

### 12. Technical Debt

Current technical debt is acceptable and mostly strategic rather than urgent.

Debt items:

- Duplicate model names across `domain`, `context`, and `market_data`.
- Mixed exception roots between general project errors and market data errors.
- Direct persistence dependency inside committee orchestration.
- `services` package contains both data service concepts and app workflow
  service concepts.
- Context provider errors are string-based.
- Provider-specific configuration is not yet generalized.
- News, filings, reports, scheduler, and analyzers are still placeholders or
  early-stage modules.
- The decision layer remains conservative and under-integrated with the
  prompt-backed committee output.

None of these require refactoring before Epic 6, but they should guide how Epic
6 is designed.

### 13. Readiness for Epic 6: News Layer

ParakeetNest is ready to begin Epic 6 if the News Layer is treated as a first
class provider-backed layer rather than as an expansion of the mock context
provider.

Epic 6 should preserve these rules:

- News providers fetch and normalize source material only.
- News providers do not call LLMs.
- Provider SDKs and HTTP clients stay inside concrete provider modules.
- Raw provider payloads do not cross the News Layer boundary.
- Every news item carries source attribution, URL when available, publication
  time when available, fetched time, and symbol or topic relevance.
- The Context Layer receives provider-neutral news models.
- Committee prompts receive rendered news context, not provider clients or raw
  JSON.
- Tests remain deterministic and network-free by default.

Readiness assessment: **Ready with guardrails**

## Major Strengths

- The architecture consistently protects the committee from direct external API
  access.
- The memory-first principle is represented in docs, models, and meeting flow.
- Provider abstractions are small, testable, and already proven by Yahoo Finance.
- SQLite v1 persistence is isolated enough for current needs.
- Application bootstrap centralizes concrete wiring.
- The default runtime remains deterministic and mock-backed.
- Tests cover both behavior and architecture boundaries.
- Documentation is unusually strong for a v0.5 codebase.

## Risks Before Phase 2

- External text ingestion can blur the boundary between facts, summaries, and
  recommendations.
- News providers may introduce inconsistent source attribution unless a shared
  model is defined early.
- Configuration may grow unevenly across provider families.
- Duplicate model names may become confusing as more data layers arrive.
- The context layer may become a catch-all if provider-backed layers are not
  kept separate.
- Persistence coupling in orchestration could make future replay, simulation, or
  alternate storage harder.
- Recommendation policy still needs a stronger typed bridge from chairman output
  to final recommendation records.

## Recommended Refactorings

No refactoring is required as part of this review. Recommended future
refactorings, in priority order:

1. Align context provider IDs between documentation and bootstrap.
2. Define naming guidance for `symbol` versus `ticker`.
3. Introduce shared source/citation value objects before or during Epic 6.
4. Make market data errors inherit from the project root error, or document why
   they intentionally do not.
5. Replace direct repository coupling in committee orchestration with a narrow
   persistence protocol when replay or alternate storage becomes necessary.
6. Split data collection services and application workflow services if
   `services` grows further.
7. Clarify model-family responsibilities in docs: collected domain facts,
   provider-layer facts, context aggregates, ORM rows, and recommendation
   records.

## Architecture Recommendations

- Use the Market Data Layer as the template for new provider-backed layers.
- Keep the Context Layer as an assembly layer, not a fetching layer.
- Keep LLM calls out of providers and raw data services.
- Treat source attribution as a domain concern, not as optional metadata.
- Prefer typed provider-neutral errors over strings for new external data
  layers.
- Keep mock providers first-class and deterministic.
- Add architecture boundary tests whenever a new provider SDK is introduced.
- Make configuration failure modes consistent across provider registries.
- Preserve the rule that every recommendation includes action, confidence,
  horizon, evidence, risks, and catalysts.

## Epic 6 Readiness Assessment

Epic 6 can start now.

Recommended Epic 6 architecture:

```text
AppConfig.news
  -> NewsProviderRegistry
  -> NewsProvider
  -> NewsService
  -> NewsContextProvider
  -> ContextService
  -> MeetingService
  -> Committee
```

Minimum Epic 6 deliverables:

- provider-neutral news models;
- provider-neutral news error hierarchy;
- `NewsProvider` protocol;
- deterministic mock news provider;
- one optional live or fixture-backed provider if desired;
- `NewsProviderRegistry`;
- `NewsService`;
- context adapter from news service to `MeetingContext.news`;
- tests for normalization, source attribution, provider errors, registry
  selection, config behavior, and SDK isolation;
- architecture documentation for the News Layer.

Epic 6 should not add automatic trading, hard-coded API keys, or LLM-based news
summarization inside the provider layer.

## Proposed Roadmap: Epic 6 to Epic 10

### Epic 6: News Layer

Goal: Add a provider-backed, source-attributed news ingestion layer.

Expected architecture outcomes:

- News provider abstraction and registry.
- Provider-neutral news item and news snapshot models.
- Deterministic mock provider as default.
- Optional live provider behind configuration.
- News context adapter integrated into the existing context pipeline.
- Documentation and boundary tests for provider SDK isolation.

### Epic 7: Filings and Fundamental Documents Layer

Goal: Add source-attributed SEC filings or company document context.

Expected architecture outcomes:

- Filing provider abstraction and registry.
- Filing metadata and excerpt models.
- Clear distinction between raw filing facts and committee interpretation.
- Context integration for filings.
- Tests for accession numbers, filing dates, URLs, and missing data behavior.

### Epic 8: Recommendation Policy and Decision Persistence

Goal: Strengthen the bridge from committee output to durable recommendation
records.

Expected architecture outcomes:

- Typed chairman output parsing into recommendation models.
- Policy validation for required recommendation fields.
- Persistence path for recommendations.
- Data-confidence and evidence provenance checks.
- Tests that incomplete recommendations fail safely.

### Epic 9: Report Generation

Goal: Produce daily or weekly research reports from recommendations, context,
committee outputs, and memory.

Expected architecture outcomes:

- Report service and report models.
- Report rendering separated from data fetching.
- SQLite persistence for generated reports.
- Deterministic report tests.
- Optional CLI command for report generation.

### Epic 10: Scheduling and Operational Runtime

Goal: Introduce scheduled research workflows without embedding investment logic
in scheduler code.

Expected architecture outcomes:

- Scheduler triggers application services only.
- Job definitions remain thin and testable.
- Runtime logging and failure handling are standardized.
- No automatic trading.
- No hidden provider credentials in job definitions.

## Final Assessment

ParakeetNest v0.5 is architecturally healthy. The project has earned the right
to add more real-world data, but only if Epic 6 preserves the provider
discipline established by the Market Data Layer. The next milestone should
avoid broad refactoring and instead add the News Layer as another small,
provider-neutral, test-first boundary.
