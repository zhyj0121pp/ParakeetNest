# Project ParakeetNest

Three Parakeets. One Committee. Better Investment Decisions.

ParakeetNest is an AI investment research platform where Xixi, Dongdong, and
Yoyo debate, remember, and continuously learn. The committee remembers before
it reasons, and every recommendation must include action, confidence, horizon,
evidence, risks, and catalysts.

## Current Status

ParakeetNest v1.0 is complete and frozen as the Phase I architecture baseline.
The platform is a committee-driven investment advisory system, not a
research-pipeline-first system. The governing product flow is:

```text
Facts -> Context -> LLM Committee -> Investment Judgment -> Human Decision
```

The platform now has a memory-first committee workflow, SQLite-backed
committee memory and meeting persistence, a provider-neutral Context Layer,
an LLM runtime boundary with deterministic mock support, and repeatable Data
Source Layer patterns for market data, Yahoo Finance, news, SEC filings,
financial statements, valuation, portfolio context, watchlists, and macro and
investment-intelligence context.

The committee produces advisory investment judgments and local daily reports.
Reports present committee judgment; they do not replace the operator. Human
decision remains final. Automatic trading is not implemented, API keys are not
hard-coded, and deterministic mock providers remain first-class for local
development and tests.

Phase II planning starts after this v1.0 architecture freeze. New work should
build on the completed boundaries instead of changing the v1.0 model contracts
without an explicit architecture decision.

## Project Layout

- `src/parakeetnest/app.py`: application bootstrap and dependency wiring.
- `src/parakeetnest/committee`: committee roles, prompts, runtime, memory, and
  meeting orchestration.
- `src/parakeetnest/context`: context provider registry, provider contracts,
  context assembly, and prompt rendering for committee meetings.
- `src/parakeetnest/llm`: LLM provider boundary, mock provider, schemas, and
  parsing utilities.
- `src/parakeetnest/intelligence`: investment-intelligence services and
  context adapters for regime, sector rotation, breadth, momentum, sentiment,
  health, and risk.
- `src/parakeetnest/portfolio`: portfolio provider, models, service, context
  adapter, and portfolio committee support.
- `src/parakeetnest/market_data`, `src/parakeetnest/news`,
  `src/parakeetnest/macro`, `src/parakeetnest/valuation`,
  `src/parakeetnest/watchlist`: provider-neutral fact and context layers.
- `src/parakeetnest/sec`: SEC filing domain models, provider protocol, mock and
  EDGAR providers, registry, and service boundary.
- `src/parakeetnest/financials`: financial statement domain models, provider
  interface, mock provider, registry, service boundary, and context adapter.
- `src/parakeetnest/services`: retained v1 compatibility package for legacy
  data collection, validation, and `MeetingService` application orchestration.
- `src/parakeetnest/domain.py`: legacy normalized snapshot boundary for the
  original collection and persistence path.
- `src/parakeetnest/decision`: shared recommendation model exports.
- `src/parakeetnest/memory`: investment knowledge base and historical memory.
- `src/parakeetnest/database`: SQLite v1 connection, schema, and repository
  adapters.
- `src/parakeetnest/research`: committee-centered research report composition,
  rendering, and delivery services.
- `src/parakeetnest/reports`: local daily report orchestration, archive writes,
  explicit output writes, and provider-neutral email handoff.
- `tests`: pytest coverage for architecture boundaries and v1 behavior.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

For live-provider validation, install the optional provider dependencies:

```bash
.venv/bin/python -m pip install -e ".[dev,openai,yahoo,robinhood,gmail]"
```

After install, the package exposes a local CLI:

```bash
source .venv/bin/activate
parakeetnest --help
```

Without activating the virtualenv, use `.venv/bin/parakeetnest ...`.

## Documentation

- [Documentation Overview](docs/README.md)
- [Clean Machine Validation](docs/clean-machine-validation.md)
- [End-to-End Provider Integration](docs/integration.md)
- [Local Daily Report Workflow](docs/architecture/automated-daily-report-flow.md)
- [Context Layer Architecture](docs/architecture/context-layer.md)
- [Domain Model Boundary](docs/architecture/domain-model-boundary.md)
- [Market Data Layer Architecture](docs/architecture/market-data-layer.md)
- [Data Source Layer Architecture](docs/architecture/data-source-layer.md)
- [Architecture Milestone Review v1.1](docs/architecture/architecture-milestone-review-v1.1.md)
- [Architecture Milestone Review v1.0](docs/architecture/architecture-milestone-review-v1.0.md)
- [Architecture Milestone Review v0.8](docs/architecture/milestone-review-v0.8.md)
- [Architecture Milestone Review v0.7](docs/architecture/milestone-review-v0.7.md)
- [Epic Index](docs/epics/README.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Local Configuration

Create a local environment file from the example:

```bash
cp .env.example .env
```

Fill real provider credentials only in `.env`. Do not commit `.env`,
`secrets/`, `.gmail-token/`, or `.robinhood-session/`.

Runtime settings such as database path use the `PARAKEETNEST_` prefix.
Live provider credentials intentionally use the provider-neutral names shown in
`.env.example` and `examples/config-real.toml`, such as `OPENAI_API_KEY`,
`FRED_API_KEY`, `SEC_USER_AGENT`, and `ROBINHOOD_USERNAME`.

Before running live-provider commands from a shell, export the `.env` values
into the process:

```bash
set -a
source .env
set +a
```

Useful local settings:

- `PARAKEETNEST_ENVIRONMENT`: `development`, `test`, or `production`.
- `PARAKEETNEST_LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or
  `CRITICAL`.
- `PARAKEETNEST_LOG_JSON`: `true` for structured JSON logs.
- `PARAKEETNEST_SQLITE_PATH`: SQLite database path.
- `OPENAI_API_KEY`: required for the OpenAI LLM provider.
- `PARAKEETNEST_LLM_PROVIDER`: `mock` or `openai`.
- `PARAKEETNEST_LLM_MODEL`: model name for the configured LLM provider.
- `PARAKEETNEST_LLM_TEMPERATURE`: model temperature, usually `0.0` for reports.
- `FRED_API_KEY`: required for the FRED macro provider.
- `SEC_USER_AGENT`: required for SEC EDGAR. Quote it in `.env` if it contains
  spaces.
- `GOOGLE_APPLICATION_CREDENTIALS`: Gmail OAuth client credentials JSON path.
- `PARAKEETNEST_GMAIL_TOKEN_PATH`: Gmail authorized-user token JSON path.
- `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD`: Robinhood login inputs.
- `ROBINHOOD_SESSION_CACHE_PATH`: local `robin_stocks` session cache path.
- `PARAKEETNEST_REPORT_RECIPIENT`: recipient for local live report delivery.

Validate live-provider configuration without making external API calls:

```bash
parakeetnest doctor --config examples/config-real.toml
```

Mock-mode local checks do not need live credentials:

```bash
parakeetnest doctor
parakeetnest meeting "Should I buy NVDA now?" --ticker NVDA
parakeetnest daily-report --mode morning --tickers NVDA AAPL --archive
parakeetnest schedule print-plist
```

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
invalid numeric values for the retained legacy snapshot path. Tests use
manually constructed snapshots and deterministic mock data.

## Legacy Mock Data Collection

This package is retained for v1 compatibility and historical data-quality
coverage. It is not the main product flow. The main v1 flow is committee-first:
facts are adapted into context, the LLM committee reasons over that prepared
context and memory, reports present committee judgment, and the human operator
makes the final decision.

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

The retained collection layer owns service interfaces, mock services,
validation, and orchestration for the legacy snapshot path. It does not import
SQLAlchemy ORM models. Persistence mapping lives in
`src/parakeetnest/database/snapshot_repository.py`, where validated domain
snapshots are converted into SQLite records and `data_quality_reports`
metadata rows.

New v1 product work should follow the provider -> service -> context provider
pattern documented in the Data Source Layer, not add new product behavior to
the legacy collection package.

The Context Layer is documented in
[`docs/architecture/context-layer.md`](docs/architecture/context-layer.md). It
defines how providers are registered, configured, merged, and rendered into
committee prompts.

The SEC Filing Layer follows the shared Data Source Layer pattern documented in
[`docs/architecture/data-source-layer.md`](docs/architecture/data-source-layer.md)
and summarized in
[`docs/epics/epic-007-sec-filing-layer.md`](docs/epics/epic-007-sec-filing-layer.md).

The Financial Statement Layer follows the same pattern and is documented in
[`docs/epics/epic-008-financial-statement-layer.md`](docs/epics/epic-008-financial-statement-layer.md).

Epic 003 summarizes the Context Pipeline Refinement work in
[`docs/epics/epic-003-context-pipeline-refinement.md`](docs/epics/epic-003-context-pipeline-refinement.md).

## Committee Flow

Committee meetings are the center of the product. Source-specific providers and
intelligence services prepare facts, `ContextService` assembles prompt-ready
context, the committee reasons over that context and remembered history, and
the Chairman produces an investment judgment for a human operator.

A meeting follows the required memory-first sequence:

1. Investment Secretary loads historical thesis and discussion context.
2. Xixi reviews fundamentals.
3. Dongdong reviews opportunity.
4. Yoyo reviews risk.
5. Chairman summarizes the committee opinions.
6. Investment Secretary records the discussion.

The local runtime can use deterministic mock LLM/provider implementations for
tests and development. No committee path places trades or performs autonomous
brokerage activity.

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
