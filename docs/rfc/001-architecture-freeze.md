# RFC-001: Architecture Freeze After Milestone 6

Status: Accepted
Date: 2026-06-29
Milestone: 6.5

## Summary

ParakeetNest is frozen around a memory-first investment research architecture.
The system collects and validates normalized investment facts, stores
historical records in SQLite, recalls investment memory, runs a deterministic
committee workflow, and produces conservative recommendation objects.

This RFC freezes the package boundaries before OpenAI, real market data,
scheduling, report generation, and email are added. The main rule is:

The committee remembers before it reasons.

## Current Architecture After Milestone 6

The current implementation contains no automatic trading, no external API
calls, no OpenAI calls, and no hard-coded API keys. Deterministic mock services
are used until real providers are introduced.

Current flow:

1. `services` collect normalized snapshots from deterministic mock services.
2. `services.data_quality` validates source, fetch time, freshness, required
   fields, missing fields, numeric sanity, and confidence.
3. `services.orchestrator` coordinates collection and validation.
4. `database.snapshot_repository` persists validated snapshots and their data
   quality metadata to SQLite.
5. `memory.knowledge_base` stores accumulated investment knowledge, including
   thesis history, committee discussions, research notes, and lessons learned.
6. `committee.secretary` recalls thesis and discussion context before any
   committee member reviews a symbol.
7. `committee` members produce deterministic opinions.
8. `committee.chairman` summarizes the opinions into a typed committee output.
9. `committee.secretary` records the discussion back into memory.
10. `decision` currently exposes a conservative placeholder recommendation
    engine.
11. `reports` and `scheduler` remain placeholders for future milestones.

## Package Responsibilities

### `parakeetnest.domain`

Defines normalized data snapshots shared between collection, validation,
persistence, and future analyzers. These are provider-neutral facts such as
portfolio holdings, market data, financials, news, macro observations, and
calendar events.

### `parakeetnest.models`

Defines shared investment decision models, including recommendation actions,
confidence levels, investment horizons, evidence items, recommendations, and
committee memos.

### `parakeetnest.services`

Owns data-service protocols, deterministic mock implementations, data quality,
and collection orchestration. Services return normalized domain snapshots and
do not return provider-specific payloads.

The services package must not know SQLAlchemy ORM models, OpenAI clients, email
clients, or trading/broker execution APIs.

### `parakeetnest.database`

Owns SQLite v1 persistence, SQLAlchemy models, engine/session setup, schema
initialization, generic repositories, and snapshot persistence adapters.

This package is allowed to map normalized domain snapshots into ORM rows. It is
also allowed to persist data quality reports. It should not collect market data,
call LLMs, run committee reasoning, or make recommendation policy decisions.

### `parakeetnest.memory`

Owns investment memory: append-only thesis history, committee discussions,
research notes, lessons learned, and recall helpers.

The knowledge base is intentionally separate from the historical database. It
stores interpreted investment knowledge, not raw market facts.

### `parakeetnest.committee`

Owns the investment committee workflow and member roles:

- Xixi: Chief Fundamental Analyst.
- Dongdong: Chief Opportunity Hunter.
- Yoyo: Chief Risk Officer.
- Chairman: final committee summarizer.
- Investment Secretary: memory keeper.

The committee consumes recalled memory and current facts. It does not fetch
external data directly and does not persist raw market snapshots.

### `parakeetnest.decision`

Owns recommendation policy and recommendation exports. Today it is a
conservative placeholder. Future versions should consume typed committee
outputs and validated evidence, then produce recommendations that include
action, confidence, horizon, evidence, risks, and catalysts.

### `parakeetnest.analyzers`

Reserved for typed analysis modules such as portfolio, stock, market, risk,
opportunity, catalyst, and thesis analysis. These modules should consume
validated domain data and memory context rather than provider-specific data.

### `parakeetnest.reports`

Reserved for daily, weekly, and monthly research report generation. Report
generation should consume recommendations, committee outputs, evidence, and
memory. It should not fetch data or call trading systems.

### `parakeetnest.scheduler`

Reserved for scheduled research workflows. The scheduler may trigger
application-level workflows, but it should not contain investment logic,
provider-specific data mapping, or LLM prompts.

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
services protocols and data quality
        |
database persistence adapters
        |
memory, analyzers, committee, decision
        |
reports and scheduler workflows
```

Important boundary:

`services.orchestrator` depends on the `SnapshotPersistence` protocol, not on
SQLAlchemy ORM models. The concrete implementation currently lives in
`database.snapshot_repository`.

## Why Data Services Do Not Call LLM

Data services are responsible for collection, normalization, and validation.
They should return facts with source and freshness metadata.

LLM calls belong behind a future LLM provider interface and should be used by
committee reasoning or report generation, not by raw data services. Keeping
LLMs out of services prevents:

- fabricated facts entering the historical database;
- hidden reasoning inside collection code;
- hard-to-test service behavior;
- provider-specific prompts leaking into normalized data models;
- confusion between observed facts and interpreted conclusions.

Data services may collect text such as news summaries in the future, but they
must preserve source attribution and must not turn that text into committee
judgment.

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

External data must first pass through service interfaces, normalized snapshots,
and data quality checks. The committee receives current facts and data quality
notes after those boundaries have done their job.

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

Milestone 6 implements the rule directly in `CommitteeMeeting.run`.

1. `CommitteeMeeting.run` calls `InvestmentSecretary.load_context`.
2. The secretary recalls thesis history and committee discussion history from
   `KnowledgeBase`.
3. The secretary builds an `InvestmentContext` containing:
   - `historical_thesis`;
   - `historical_discussions`;
   - `current_facts`;
   - `data_quality_notes`.
4. Xixi, Dongdong, and Yoyo review the already-loaded context.
5. The Chairman summarizes the opinions.
6. The secretary records the discussion back to the knowledge base.

The important invariant is that committee members receive `InvestmentContext`
after memory has been loaded. They do not independently query memory or fetch
new external facts while reviewing.

## Known Tradeoffs

- The committee is deterministic and rule-based until LLM integration exists.
  This preserves testability but limits reasoning depth.
- Mock services are intentionally deterministic. They make development stable
  but do not represent real market coverage.
- SQLite v1 is simple and portable, but schema evolution will need migrations
  before real long-lived data accumulates.
- `parakeetnest.models`, `parakeetnest.domain`, `committee.models`, and
  `memory.models` define separate model vocabularies. The separation is useful,
  but future contributors must keep boundaries clear.
- The knowledge base is currently in-memory. Persistence exists in database
  models for memory-like records, but repository-backed knowledge recall is not
  complete.
- Report generation, scheduler jobs, and analyzers are placeholders.
- Data quality metadata is persisted for saved snapshots, but richer quality
  policy and provider-specific diagnostics are still future work.
- The current application has package boundaries but not a full import-linter
  configuration. Tests cover the most important services-to-database boundary.

## Open Questions Before OpenAI Integration

- What exact `LLMProvider` protocol should the committee use?
- Should the provider interface accept raw prompts, typed request objects, or
  role-specific committee tasks?
- What JSON schema should each committee member return?
- How strict should schema validation be when an LLM returns partial or invalid
  output?
- Where should prompt templates live?
- How should cited evidence be represented so the Chairman cannot invent
  unsupported conclusions?
- Should OpenAI calls happen only in committee members, only in a committee
  engine, or behind a separate reasoning service?
- How should LLM outputs be logged without leaking secrets or excessive
  personal financial data?
- What retry, timeout, and fallback behavior should be used?
- How should deterministic tests cover LLM-backed behavior?
- Which memory records should be included in prompts, and how should recall be
  capped?
- How will recommendation confidence distinguish data quality confidence from
  committee reasoning confidence?

## Non-Goals

- Do not implement OpenAI in this milestone.
- Do not implement external market data APIs in this milestone.
- Do not implement email delivery in this milestone.
- Do not implement automatic trading.
- Do not store API keys in code.
