# RFC-001: v1.0 Architecture Freeze

Status: Accepted
Date: 2026-06-29
Updated: 2026-07-02
Milestone: v1.0

## Summary

ParakeetNest v1.0 is frozen around a memory-first, committee-driven investment
advisory architecture. The platform prepares facts into context, recalls
committee memory before reasoning, runs an LLM-backed investment committee, and
returns advisory investment judgment for a human operator.

The main rule is:

The committee remembers before it reasons.

The v1.0 product thesis is:

```text
Facts -> Context -> LLM Committee -> Investment Judgment -> Human Decision
```

ParakeetNest is not a research-pipeline-first system and is not an autonomous
trading system. Reports present committee judgment. Human decision remains
final.

## Current Architecture At v1.0

The current implementation contains no automatic trading and no hard-coded API
keys. Provider-specific integrations are isolated behind provider protocols and
registries. Deterministic mock providers remain first-class for local
development and tests.

Current flow:

1. Fact providers and source services normalize market, news, SEC filing,
   financial statement, valuation, macro, portfolio, watchlist, and investment
   intelligence inputs.
2. Context providers adapt those facts into `MeetingContext` sections.
3. `ContextService` merges enabled context providers into one prepared meeting
   context.
4. Committee memory is recalled before agent reasoning.
5. The LLM committee runtime gives Xixi, Dongdong, Yoyo, and the Chairman
   prompt-ready context and memory.
6. The Chairman produces an investment judgment with action, confidence,
   horizon, evidence, risks, and catalysts.
7. The Investment Secretary records committee memory.
8. Local daily reports and research outputs present committee judgment for
   human review.

Retained v1 compatibility flow:

1. `services` still contains deterministic mock collection services, data
   quality validation, and `DataCollectionOrchestrator`.
2. `database.snapshot_repository` still persists validated legacy snapshots and
   their data quality metadata to SQLite.
3. This legacy collection path is retained for compatibility and tests. It is
   not the main v1 product flow.

## Package Responsibilities

### `parakeetnest.domain`

Defines legacy normalized data snapshots shared between collection,
validation, and snapshot persistence. These are provider-neutral facts such as
portfolio holdings, market data, financials, news, macro observations, and
calendar events. The package is retained for v1 compatibility.

### `parakeetnest.models`

Defines shared investment decision models, including recommendation actions,
confidence levels, investment horizons, evidence items, recommendations, and
committee memos.

### `parakeetnest.services`

Owns two v1 responsibilities:

- `MeetingService`, the current application service for running committee
  meetings.
- Retained legacy data-service protocols, deterministic mock implementations,
  data quality, and collection orchestration.

The services package must not know SQLAlchemy ORM models, OpenAI clients, email
clients, or trading/broker execution APIs.

### `parakeetnest.database`

Owns SQLite v1 persistence, SQLAlchemy models, engine/session setup, schema
initialization, meeting repositories, committee memory repositories, and
snapshot persistence adapters.

This package is allowed to map normalized domain snapshots into ORM rows. It is
also allowed to persist data quality reports. It should not collect market data,
call LLMs, run committee reasoning, or make recommendation policy decisions.

### `parakeetnest.memory` and `parakeetnest.committee.memory`

Own investment memory: append-only thesis history, committee discussions,
research notes, lessons learned, committee memory records, and recall helpers.

The knowledge base is intentionally separate from the historical database. It
stores interpreted investment knowledge, not raw market facts.

### `parakeetnest.committee`

Owns the investment committee workflow and member roles:

- Xixi: Chief Fundamental Analyst.
- Dongdong: Chief Opportunity Hunter.
- Yoyo: Chief Risk Officer.
- Chairman: final committee summarizer.
- Investment Secretary: memory keeper.

The committee consumes recalled memory and prepared context. It does not fetch
external data directly, query provider registries, or persist raw market
snapshots.

### `parakeetnest.context`

Owns `ContextRequest`, `MeetingContext`, context providers, context provider
registry, context assembly, and prompt rendering. This is the bridge between
facts and committee reasoning.

### `parakeetnest.llm`

Owns the LLM provider boundary, mock LLM provider, parsing, schemas, and prompt
support. LLM behavior is accessed through explicit interfaces and deterministic
test doubles.

### Data Source and Intelligence Packages

Packages such as `market_data`, `news`, `sec`, `financials`, `macro`,
`valuation`, `portfolio`, `watchlist`, `regime`, and `intelligence` own
provider-neutral source models, provider protocols, services, calculators, and
context adapters. They prepare facts for context and do not make final
investment decisions.

### `parakeetnest.decision`

Owns shared recommendation model exports. Final v1 investment judgment is
committee-led and human-reviewed.

### `parakeetnest.research` and `parakeetnest.reports`

Own research report composition, rendering, local daily report orchestration,
local archive writes, explicit output writes, and provider-neutral email
handoff.

Reports present committee judgment. They should not fetch raw data directly,
invent recommendation policy outside the committee, or call trading systems.

### Foundation Packages

- `config` loads application settings.
- `logging` configures logging.
- `exceptions` defines project exceptions.
- `runtime` bootstraps application runtime concerns.

## Dependency Direction

Dependencies should point inward toward stable models and outward only through
explicit interfaces.

Preferred direction:

```text
config / logging / exceptions
        |
domain and shared models
        |
source services, intelligence services, and legacy data quality
        |
context providers and ContextService
        |
committee memory and LLM committee runtime
        |
investment judgment and local report workflows
        |
human decision
```

Important boundary:

`services.orchestrator` depends on the `SnapshotPersistence` protocol, not on
SQLAlchemy ORM models. The concrete implementation currently lives in
`database.snapshot_repository`.

## Why Fact Services Do Not Call LLM

Fact services are responsible for provider access, normalization, calculations,
and source metadata. Legacy data services additionally validate retained
snapshot objects.

LLM calls belong behind the LLM provider interface and are used by committee
reasoning, not by raw data services. Keeping LLMs out of fact services
prevents:

- fabricated facts entering the historical database;
- hidden reasoning inside collection code;
- hard-to-test service behavior;
- provider-specific prompts leaking into normalized data models;
- confusion between observed facts and interpreted conclusions.

Fact services may collect text such as news summaries, but they must preserve
source attribution and must not turn that text into committee judgment.

## Why Committee Engine Does Not Access External APIs Directly

The committee engine is responsible for reasoning over available evidence and
memory. It should not fetch market data, news, brokerage data, macro data, or
calendar events directly.

This keeps the committee:

- deterministic and testable;
- focused on debate and recommendation structure;
- independent from provider outages and rate limits;
- protected from mixing unvalidated data into reasoning;
- compatible with the memory-first rule.

External data must first pass through provider interfaces, source services, and
context providers. The committee receives prepared context after those
boundaries have done their job.

## Why Knowledge Base Is Separate From Historical Database

The historical database stores observed facts and persistence records:
holdings, market snapshots, financial data, news items, macro observations,
calendar events, recommendations, reports, and data quality reports.

The knowledge base stores interpreted investment memory:
thesis versions, committee discussion summaries, research notes, and lessons
learned.

The separation matters because raw facts and investment knowledge have
different lifecycles:

- raw facts are time-series evidence;
- knowledge evolves through append-only thesis versions;
- committee memory must be recalled before reasoning;
- analysis should be able to cite both current data and historical thinking;
- future LLM prompts should receive curated memory, not unbounded raw database
  rows.

SQLite may persist both categories in v1, but the conceptual boundary remains:
the historical database is evidence storage; the knowledge base is investment
memory.

## How Remember Before Reasoning Is Implemented

v1.0 implements the rule in committee runtime and meeting orchestration.

1. `MeetingService` creates the meeting lifecycle and builds `ContextRequest`.
2. `ContextService` assembles prepared context from registered context
   providers.
3. Committee memory is searched before agent prompt execution.
4. Xixi, Dongdong, and Yoyo review the already-loaded context and remembered
   history.
5. The Chairman summarizes the opinions into investment judgment.
6. The Investment Secretary records the discussion back to committee memory.

The important invariant is that committee members receive prepared context
after memory has been loaded. They do not independently query memory or fetch
new external facts while reviewing.

## Known Tradeoffs

- Mock providers are intentionally deterministic. They make development stable
  but do not represent complete market coverage.
- SQLite v1 is simple and portable, but schema evolution will need migrations
  before real long-lived data accumulates.
- `parakeetnest.models`, `parakeetnest.domain`, `committee.models`, and
  `memory.models` define separate model vocabularies. The separation is useful,
  but future contributors must keep boundaries clear.
- Legacy `services` data collection remains in the tree for v1 compatibility
  and tests, but it is not the main product flow.
- Data quality metadata is persisted for saved snapshots, but richer quality
  policy and provider-specific diagnostics are still future work.
- The current application has package boundaries but not a full import-linter
  configuration. Tests cover the most important boundaries.

## Non-Goals

- Do not implement automatic trading.
- Do not store API keys in code.
- Do not let reports or CLI workflows make autonomous investment decisions.
- Do not let committee agents fetch provider data directly.
