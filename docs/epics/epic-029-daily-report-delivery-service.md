# Epic 29 - Daily Report Delivery Service

## Goal

Add the application-level use case a future scheduler can call to compose and
deliver the daily investment report.

## Scope

- Add `DailyReportDeliveryRequest` and `DailyReportDeliveryService` under
  `src/parakeetnest/research/daily_delivery.py`.
- Accept requested tickers, recipient email, optional `account_id`,
  `as_of_date`, `generated_at`, subject, and metadata.
- Compose the report body through `DailyInvestmentReportComposer`.
- Deliver the body through `ReportDeliveryService`.
- Build a default subject when none is supplied:
  `Daily Investment Report - YYYY-MM-DD`.

## Out of Scope

- No scheduler, CLI, automatic trading, credentials, external email provider,
  or database table.
- No Gmail, SMTP, SES, SendGrid, or other real delivery adapter.

## Architecture Decisions

`DailyReportDeliveryService` is intentionally thin. It owns the use-case
workflow only: compose the daily report body, choose the subject, and pass the
prepared body to the provider-neutral delivery service.

The service depends on composer and delivery service protocols so tests and
future schedulers can wire the use case without coupling scheduling to
research generation, rendering, subject formatting, or provider details.

Default subject dates prefer `as_of_date`, then `generated_at.date()`, then the
current local date. This keeps scheduler-provided report dates authoritative
while preserving a reasonable default for ad hoc local use.

## Acceptance Criteria

- Can compose and deliver a daily report through `NoOpReportDeliveryProvider`.
- Tests verify tickers, `account_id`, `as_of_date`, and `generated_at` pass
  through to the composer.
- Tests verify recipient, subject, body, and metadata pass through to the
  delivery service.
- Tests verify default subject generation.
- No real provider, credentials, scheduler, CLI, automatic trading, or database
  table is added.
