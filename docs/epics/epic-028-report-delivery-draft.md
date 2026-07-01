# Epic 28 - Report Delivery Draft

## Goal

Define a provider-neutral delivery abstraction for sending daily investment
reports later.

## Scope

- Add delivery models under `src/parakeetnest/research/delivery.py`.
- Model a plain-text delivery request with recipient email, subject, body, and
  optional metadata.
- Model delivery results with status, provider name, optional message id, and
  failure message.
- Define `ReportDeliveryProvider` as the adapter contract for future providers.
- Add `NoOpReportDeliveryProvider` for deterministic tests and local wiring.
- Add `ReportDeliveryService` that depends only on the provider interface.

## Out of Scope

- No real email provider integration.
- No Gmail, SMTP, SendGrid, SES, credentials, or API keys.
- No scheduler, CLI, database tables, or automatic trading.

## Architecture Decisions

`ReportDeliveryService` accepts a `ReportDeliveryProvider` protocol and never
imports a concrete external provider. This keeps delivery in the application
boundary while future Gmail, SMTP, SendGrid, or SES adapters can live behind the
same interface.

The no-op provider records requests and returns deterministic results without
sending anything. It can be configured to return a failed result so callers can
test failure paths without network access or credentials.

Provider exceptions are translated by the service into
`ReportDeliveryStatus.FAILED` results. This keeps callers working with the same
neutral output shape regardless of whether a provider reports failure directly
or raises an exception.

## Acceptance Criteria

- Can create a delivery request.
- Can deliver via no-op provider.
- Delivery result records success and failure.
- Tests cover request validation, no-op delivery, and failure behavior.
- No real email sender, scheduler, CLI, provider dependency, credentials, or
  database table is added.
