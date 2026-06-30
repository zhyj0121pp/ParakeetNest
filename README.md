# Project ParakeetNest

Three Parakeets. One Committee. Better Investment Decisions.

ParakeetNest is an AI investment research platform where Xixi, Dongdong, and
Yoyo debate, remember, and continuously learn. The committee remembers before
it reasons, and every recommendation must include action, confidence, horizon,
evidence, risks, and catalysts.

## Current Status

This repository contains the initial Python skeleton only. External API calls,
brokerage integrations, market data providers, LLM calls, email delivery, and
automatic trading are not implemented.

Milestone 1 adds the foundation layer: configuration loading, structured
logging, common exceptions, and an application bootstrap.

Milestone 2 adds the SQLite database foundation using SQLAlchemy 2.0, including
ORM models, engine/session setup, repository helpers, and database
initialization.

Milestone 3 adds normalized domain snapshots and a data quality layer that
checks source attribution, fetch time, required fields, freshness, empty values,
and numeric sanity before data is saved or analyzed.

Milestone 4 adds deterministic mock data services and a collection orchestrator
that validates snapshots and saves valid mock records to SQLite.

Milestone 4.5 cleans up architecture boundaries: collection orchestration no
longer imports ORM models directly, persistence is delegated to a database-side
snapshot persistence service, and data quality metadata is stored alongside
validated records.

Milestone 5 adds a deterministic committee engine without OpenAI. The committee
loads memory first, then Xixi, Dongdong, and Yoyo produce typed opinions,
Chairman summarizes, and the Investment Secretary records the discussion.

Milestone 6 adds an append-only knowledge base and thesis tracker. The committee
can now recall thesis history and prior discussions before member reviews.

Epic 3.5 documents the Context Layer pipeline that assembles provider data and
memory into committee prompt context before any LLM reasoning.

Epic 7 adds the SEC Filing Layer, including provider-neutral filing models, a
mock provider, an optional SEC EDGAR provider, a filing service, and context
integration through `MeetingContext.filings`.

## Project Layout

- `src/parakeetnest/committee`: committee roles and meeting orchestration.
- `src/parakeetnest/context`: context provider registry, provider contracts,
  context assembly, and prompt rendering for committee meetings.
- `src/parakeetnest/sec`: SEC filing domain models, provider protocol, mock and
  EDGAR providers, registry, and service boundary.
- `src/parakeetnest/services`: data collection and validation boundaries.
- `src/parakeetnest/domain.py`: normalized snapshot models shared across
  services, persistence, and future analyzers.
- `src/parakeetnest/analyzers`: portfolio, stock, market, catalyst, risk,
  opportunity, and thesis analyzers.
- `src/parakeetnest/decision`: recommendation and policy engine skeletons.
- `src/parakeetnest/memory`: investment knowledge base and historical memory.
- `src/parakeetnest/database`: SQLite v1 connection, schema, and repository
  scaffolding.
- `src/parakeetnest/reports`: daily, weekly, and monthly report generators.
- `src/parakeetnest/scheduler`: scheduled research workflow placeholders.
- `tests`: basic pytest coverage for the skeleton.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

## Documentation

- [Documentation Overview](docs/README.md)
- [Context Layer Architecture](docs/architecture/context-layer.md)
- [Market Data Layer Architecture](docs/architecture/market-data-layer.md)
- [Data Source Layer Architecture](docs/architecture/data-source-layer.md)
- [Architecture Milestone Review v0.7](docs/architecture/milestone-review-v0.7.md)
- [Epic Index](docs/epics/README.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Local Configuration

Create a local environment file from the example:

```bash
cp .env.example .env
```

Configuration is loaded with the `PARAKEETNEST_` prefix. Leave future
integration secrets blank until those integrations are implemented.

Useful local settings:

- `PARAKEETNEST_ENVIRONMENT`: `development`, `test`, or `production`.
- `PARAKEETNEST_LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or
  `CRITICAL`.
- `PARAKEETNEST_LOG_JSON`: `true` for structured JSON logs.
- `PARAKEETNEST_SQLITE_PATH`: future SQLite database path.

## Database

SQLite is the default v1 database. Initialize the configured database with:

```bash
.venv/bin/python - <<'PY'
from parakeetnest.config import get_settings
from parakeetnest.database import create_sqlite_engine, initialize_database

settings = get_settings()
engine = create_sqlite_engine(settings.sqlite_path)
initialize_database(engine)
print(f"Initialized {settings.sqlite_path}")
PY
```

The schema is intentionally simple for v1 and does not fetch data from external
providers.

## Data Quality

Every normalized snapshot carries source and fetch-time context. The data
quality service returns:

- `source`
- `fetched_at`
- `freshness_status`
- `missing_fields`
- `validation_status`
- `confidence_score`

Validation currently covers required fields, stale data, empty values, and
invalid numeric values. External providers are still intentionally absent; tests
use manually constructed snapshots.

## Mock Data Collection

Mock services are deterministic and do not call Robinhood, Yahoo Finance, FRED,
OpenAI, or any network service. Run a local mock collection against the
configured SQLite database with:

```bash
.venv/bin/python - <<'PY'
from parakeetnest.config import get_settings
from parakeetnest.database import (
    SnapshotPersistenceService,
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    session_scope,
)
from parakeetnest.services import DataCollectionOrchestrator

settings = get_settings()
engine = create_sqlite_engine(settings.sqlite_path)
initialize_database(engine)
session_factory = create_session_factory(engine)

with session_scope(session_factory) as session:
    persistence = SnapshotPersistenceService(session)
    result = DataCollectionOrchestrator().run(persistence)
    print(f"Saved {result.saved_records} mock records")
PY
```

## Architecture Boundaries

The collection layer owns service interfaces, mock services, validation, and
orchestration. It does not import SQLAlchemy ORM models. Persistence mapping
lives in `src/parakeetnest/database/snapshot_repository.py`, where validated
domain snapshots are converted into SQLite records and `data_quality_reports`
metadata rows.

Future provider integrations should implement the explicit service protocols
from `src/parakeetnest/services/base.py` and return typed domain snapshots.

The Context Layer is documented in
[`docs/architecture/context-layer.md`](docs/architecture/context-layer.md). It
defines how providers are registered, configured, merged, and rendered into
committee prompts.

The SEC Filing Layer follows the shared Data Source Layer pattern documented in
[`docs/architecture/data-source-layer.md`](docs/architecture/data-source-layer.md)
and summarized in
[`docs/epics/epic-007-sec-filing-layer.md`](docs/epics/epic-007-sec-filing-layer.md).

Epic 003 summarizes the Context Pipeline Refinement work in
[`docs/epics/epic-003-context-pipeline-refinement.md`](docs/epics/epic-003-context-pipeline-refinement.md).

## Committee Flow

The committee engine is deterministic for now and does not call OpenAI or any
external market service. A meeting follows the required memory-first sequence:

1. Investment Secretary loads historical thesis and discussion context.
2. Xixi reviews fundamentals.
3. Dongdong reviews opportunity.
4. Yoyo reviews risk.
5. Chairman summarizes the committee opinions.
6. Investment Secretary records the discussion.

Example:

```bash
.venv/bin/python - <<'PY'
from parakeetnest.committee.meeting import CommitteeMeeting

meeting = CommitteeMeeting.default()
result = meeting.run(
    "NVDA",
    current_facts=("AI demand growth remains visible in mock data.",),
    data_quality_notes=("validated mock data quality is medium",),
)
print(result.chairman_summary.action)
print(result.chairman_summary.rationale)
PY
```

## Knowledge Base Workflow

The knowledge base stores accumulated investment knowledge rather than raw
market data. Thesis history is append-only:

```bash
.venv/bin/python - <<'PY'
from parakeetnest.memory import KnowledgeBase, ThesisTracker
from parakeetnest.committee.meeting import CommitteeMeeting

knowledge_base = KnowledgeBase()
tracker = ThesisTracker(knowledge_base)
tracker.create_thesis("NVDA", "Own only if AI demand remains evidence-backed.")
tracker.update_thesis("NVDA", "Watch valuation while AI demand evidence improves.")
knowledge_base.add_research_note("AI demand", "Mock research note.", symbol="NVDA")
knowledge_base.add_lesson_learned("Respect uncertainty.", symbol="NVDA")

meeting = CommitteeMeeting.default(knowledge_base=knowledge_base)
result = meeting.run("NVDA")
print(result.context.historical_thesis)
PY
```
