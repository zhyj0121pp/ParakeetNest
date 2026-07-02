# Automated Daily Report Flow

Status: v1.0 release hardening note

Phase XII completes the local automated daily report flow without adding
external schedulers, Gmail, cloud deployment, or trading automation. The flow is
manual and scheduler-compatible: it gives a cron-like caller a stable command
and job wrapper, while keeping report generation, archive writes, and email
delivery inside the existing report orchestration boundary.

## Completed Flow

```text
Manual CLI
  python -m parakeetnest.cli.daily_report
    -> DailyReportRequest
    -> DailyReportOrchestrator
    -> report body on stdout
    -> optional archive
    -> optional output file
    -> optional provider-neutral email

Scheduled CLI wrapper
  python -m parakeetnest.cli.scheduled_daily_report
    -> DailyReportRequest
    -> DailyReportScheduledJob
    -> DailyReportOrchestrator.run(request)
    -> report body on stdout
```

The manual CLI remains the direct local operator entry point. It supports
morning and evening report modes, explicit tickers or configured watchlist
defaults, optional account context, optional report date, optional archive,
optional output path, and optional provider-neutral email delivery.

The scheduled CLI wrapper reuses the same request-building and orchestrator
wiring behavior. It exists so a future scheduler can trigger a stable command
without knowing how daily reports are generated, archived, or delivered.

## Responsibilities

- `parakeetnest.cli.daily_report` parses operator input, builds
  `DailyReportRequest`, builds `DailyReportOrchestrator`, and prints the report
  body.
- `parakeetnest.cli.scheduled_daily_report` parses the same report options,
  builds the same request and orchestrator, calls `DailyReportScheduledJob`, and
  prints the report body.
- `DailyReportScheduledJob` is a focused scheduler-compatible wrapper. It
  accepts a `DailyReportOrchestrator` and a `DailyReportRequest`, then returns
  the `DailyReportResult` from `orchestrator.run(request)`.
- `DailyReportOrchestrator` owns report generation, archive writes, explicit
  output writes, and provider-neutral email dispatch.
- Archive behavior stays local and deterministic through the existing daily
  report archive path conventions.
- Email behavior remains provider-neutral. The current CLI wiring uses the
  console email provider for local delivery output; no Gmail integration is
  implemented.

## v1.0 Readiness

- Automated daily reports are complete for v1.0 as a manual, local,
  scheduler-compatible flow.
- The scheduler is a manual wrapper only. ParakeetNest does not install cron,
  launchd, APScheduler, Celery, or a cloud scheduler.
- Gmail delivery and cloud cron/deployment are post-v1.0 extensions.
- The flow remains advisory research only and does not place trades, execute
  orders, or automate brokerage activity.
