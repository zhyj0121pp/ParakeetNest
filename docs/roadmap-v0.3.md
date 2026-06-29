# Roadmap v0.3

This roadmap starts from the architecture frozen after Milestone 6. It keeps
the same safety rules: no automatic trading, no hard-coded API keys, SQLite for
v1, and every recommendation includes action, confidence, horizon, evidence,
risks, and catalysts.

## Milestone 7: LLM Provider Interface

Goal: define the boundary for future language-model reasoning without binding
the committee to OpenAI directly.

Deliverables:

- Add an `LLMProvider` protocol or equivalent interface.
- Define typed request and response objects for model calls.
- Add deterministic fake provider implementations for tests.
- Add timeout, retry, and error result shapes without making network calls.
- Keep API keys in configuration only.

Acceptance criteria:

- Committee code can depend on an interface rather than a concrete provider.
- Tests can run without network access.
- No OpenAI package or API call is required yet unless explicitly chosen in a
  later milestone.

## Milestone 8: Committee JSON Schema

Goal: define strict structured outputs for Xixi, Dongdong, Yoyo, and Chairman.

Deliverables:

- JSON schema for committee member opinions.
- JSON schema for Chairman summaries.
- Validation rules for action, confidence, horizon, evidence, risks, and
  catalysts.
- Fixtures for valid and invalid model outputs.
- Clear handling for missing or unsupported fields.

Acceptance criteria:

- Invalid committee output fails closed.
- Chairman output cannot omit required recommendation fields.
- Evidence, risks, and catalysts remain structured and source-aware.

## Milestone 9: OpenAI Integration

Goal: connect the frozen LLM provider interface to OpenAI while preserving
testability and safety.

Deliverables:

- OpenAI-backed provider implementation.
- Configuration-driven model selection and API key loading.
- Prompt templates for committee roles.
- Structured-output parsing and validation.
- Unit tests with fake providers and no live network requirement.
- Optional integration test path guarded by explicit environment settings.

Acceptance criteria:

- Default test suite does not call OpenAI.
- Missing API keys fail with clear configuration errors.
- LLM output is validated before it reaches decision logic.
- No trading or brokerage action is introduced.

## Milestone 10: Report Generator

Goal: turn committee outputs and evidence into daily, weekly, and monthly
research reports.

Deliverables:

- Report data models.
- Daily report generator.
- Weekly report generator.
- Monthly report generator.
- Source and evidence sections.
- Persistence of generated reports in SQLite.

Acceptance criteria:

- Reports cite recommendation action, confidence, horizon, evidence, risks, and
  catalysts.
- Reports distinguish facts, memory, committee opinions, and Chairman
  conclusions.
- Report generation does not fetch external data directly.

## Milestone 11: Real Market Data Provider

Goal: add the first real market data provider behind existing service
interfaces.

Deliverables:

- Provider implementation returning normalized `domain` snapshots.
- Configuration for provider enablement and credentials where required.
- Rate-limit and error handling.
- Data quality validation for real provider responses.
- Tests using fixtures and fake transport.

Acceptance criteria:

- Real data enters the system only through service protocols.
- Provider payloads do not leak beyond the services boundary.
- Invalid or stale data is not persisted as valid evidence.
- Tests do not require live network calls by default.

## Milestone 12: Scheduler

Goal: run research workflows on a predictable schedule.

Deliverables:

- Scheduled jobs for data collection.
- Scheduled jobs for committee review.
- Scheduled jobs for report generation.
- Local launchd support or equivalent v1 scheduler integration.
- Idempotency and logging for each scheduled run.

Acceptance criteria:

- Scheduler triggers workflows; it does not contain investment logic.
- Failed jobs leave useful logs and do not corrupt memory or SQLite records.
- Scheduling remains optional for local development.

## Milestone 13: Email

Goal: deliver generated research reports to the user.

Deliverables:

- Email provider interface.
- Deterministic fake email provider for tests.
- Config-driven real email provider implementation.
- Plain-text and optional HTML report delivery.
- Delivery logging and failure handling.

Acceptance criteria:

- Email sends reports only; it does not trigger trades.
- Secrets are loaded from configuration, not source code.
- Tests do not send real email by default.
- Delivery failures are visible and retryable.

## Cross-Milestone Rules

- Keep modules small and testable.
- Preserve dependency boundaries from `docs/dependency-boundaries.md`.
- Add real providers behind interfaces.
- Keep deterministic fakes for tests.
- Validate data before persistence or reasoning.
- Recall memory before committee reasoning.
- Keep trading out of scope.
