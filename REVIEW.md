# Project ParakeetNest Architecture Review

Staff Software Engineer review of the current implementation against
`docs/design.md`.

## Strengths

- The repository follows the design document's top-level decomposition well:
  `committee`, `services`, `database`, `memory`, `decision`, `reports`,
  `scheduler`, and `analyzers` are all present and easy to discover.
- The project respects the current safety constraints. There are no Robinhood,
  Yahoo Finance, FRED, OpenAI, email, or automatic trading calls.
- The foundation is small, typed, and testable. Configuration, logging,
  exceptions, runtime bootstrap, SQLite setup, data quality validation, and
  mock services are isolated enough to evolve incrementally.
- The SQLite layer uses SQLAlchemy 2.0 style APIs and has tests against
  temporary databases, which is the right early direction for portability and
  confidence.
- The normalized snapshot models are a good boundary between data collection
  and downstream analysis. They avoid leaking provider-specific shapes into
  the rest of the system.
- Data quality is treated as a first-class concern, matching the design rule
  that analysis should not consume unvalidated data.
- Mock data is deterministic and covered by unit tests, which creates a useful
  local development loop before external integrations exist.
- Recommendation domain objects already preserve the required contract:
  action, confidence, horizon, evidence, risks, and catalysts.

## Weaknesses

- Dependency direction is starting to bend in `DataCollectionOrchestrator`.
  The services package imports SQLAlchemy ORM models and writes directly to the
  database. This couples collection orchestration, validation, mapping, and
  persistence in one place.
- There are two parallel model vocabularies: `parakeetnest.models` for
  committee/recommendation objects and `parakeetnest.domain` for normalized
  snapshots. Both are reasonable, but the boundary is not documented and could
  become confusing as analysis and decision logic grow.
- The database schema stores historical facts but does not persist data quality
  metadata. The design requires every dataset to carry source, fetch time,
  freshness, validation status, missing fields, and confidence score.
- Mock service class aliases such as `PortfolioService = MockPortfolioService`
  are convenient now but risky later. They blur the distinction between
  provider interfaces, mock implementations, and eventual real integrations.
- The repository layer is only a generic CRUD helper. It is fine for scaffolding
  but does not yet express domain queries such as latest market snapshot,
  current thesis, discussions by symbol, or recommendations by horizon.
- Committee workflow is not yet aligned with the core principle "remembers
  before it reasons." `CommitteeMeeting` calls role reviews directly without a
  memory retrieval dependency or historical thesis context.
- The data quality service is a single module containing status models,
  required-field policy, numeric validation, freshness logic, and service
  orchestration. This is still manageable, but it will become a change hotspot.
- Naming is mostly clear, but some table names differ from the design doc
  (`financial_data` vs `financials`, `macro_data` vs `macro`, `news_items` vs
  `news`). The implementation names are more explicit, but the mismatch should
  be intentional and documented.
- There is no migration strategy. `Base.metadata.create_all()` is acceptable
  for v1 scaffolding, but schema evolution will become painful without Alembic
  or a lightweight migration plan.

## Recommended Improvements

1. Introduce a persistence adapter layer between services and database.
   `DataCollectionOrchestrator` should coordinate collection and validation,
   then delegate saving to a `SnapshotRepository` or `SnapshotPersistenceService`.
   This keeps service orchestration independent of SQLAlchemy ORM details.

2. Persist data quality metadata with collected records. A simple v1 approach
   could add `data_quality` JSON columns or a separate `data_quality_reports`
   table keyed by dataset type and record id.

3. Define package dependency rules explicitly:
   `domain` -> no project dependencies;
   `services` -> domain and data quality only;
   `database` -> ORM and persistence;
   `application/orchestration` -> coordinates services and repositories;
   `committee/decision/analyzers` -> consume validated domain data and memory.

4. Move mock implementations into a clearer namespace before adding real
   providers, for example `services/mock/portfolio.py` and later
   `services/providers/yahoo.py`. Keep `PortfolioService` as a protocol or
   abstract interface, not an alias to the mock.

5. Add typed analysis result models before analyzer logic grows. Returning
   `dict[str, object]` from analyzers will make decision logic brittle.

6. Create domain-specific repositories for core workflows:
   holdings snapshots, market snapshots, theses, discussions, recommendations,
   and reports. Keep the generic repository as an implementation helper.

7. Make "remember before reasoning" an explicit application workflow. The
   committee meeting should accept recalled thesis/discussion context before
   Xixi, Dongdong, Yoyo, and the Chairman produce outputs.

8. Add tests that assert architectural boundaries. Even simple import-linter
   style tests can prevent `services` from depending directly on ORM models once
   the persistence adapter exists.

9. Add migration planning before real data accumulates. Alembic is the normal
   SQLAlchemy path, but a minimal migration runner would also work for SQLite
   v1 if the project wants to stay lightweight.

10. Add README architecture diagrams or a short dependency map. The current
    README explains milestones well, but future contributors will benefit from
    knowing which package may depend on which.

## Technical Debt

- `DataCollectionOrchestrator` mixes collection, validation, mapping, and
  persistence.
- Data quality reports are computed but not stored in SQLite.
- Mock services use shared hard-coded data in service modules rather than
  fixtures or a mock data provider object.
- Analyzer, memory, report, scheduler, and decision packages are still
  placeholders. That is acceptable for milestones, but their public APIs may
  need revision before real behavior lands.
- ORM models and domain models require manual mapping. The mapping currently
  lives in the orchestrator and will duplicate as more flows appear.
- No migrations, no uniqueness constraints, and limited indexing beyond symbols
  and a few event fields.
- The `Recommendation` name exists both as a domain dataclass and an ORM model,
  which may cause import confusion.
- Logging is global root logger configuration. Fine for now, but libraries and
  tests may eventually need less invasive configuration.
- `.DS_Store` and `.pytest_cache` have appeared locally; `.gitignore` covers
  this, but the repo should stay source-only.

## Architecture Score

**7 / 10**

The current codebase is a strong early foundation: small modules, good tests,
safe mock data, typed snapshots, and a clear first pass at the designed layers.
The score is not higher because the most important future scalability boundary
is already under pressure: service orchestration directly persists ORM models.
Fixing that dependency direction soon will keep ParakeetNest from turning into
a collection of scripts and preserve the design's committee-memory-database
architecture as real providers and reasoning are added.
