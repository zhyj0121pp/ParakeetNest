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

## Project Layout

- `src/parakeetnest/committee`: committee roles and meeting orchestration.
- `src/parakeetnest/services`: data collection and validation boundaries.
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
