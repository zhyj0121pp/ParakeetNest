# Local Daily Report Workflow

Status: v1.0 release hardening note

Phase XII keeps the daily report flow local and manual without adding external
schedulers, Gmail, cloud deployment, or trading automation. The operator runs
the daily report CLI directly, while report generation, archive writes, explicit
output writes, and email delivery stay inside the existing report orchestration
boundary.

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
```

The manual CLI remains the direct local operator entry point. It supports
morning and evening report modes, explicit tickers or configured watchlist
defaults, optional account context, optional report date, optional archive,
optional output path, and optional provider-neutral email delivery.

## Responsibilities

- `parakeetnest.cli.daily_report` parses operator input, builds
  `DailyReportRequest`, builds `DailyReportOrchestrator`, and prints the report
  body.
- `DailyReportOrchestrator` owns report generation, archive writes, explicit
  output writes, and provider-neutral email dispatch.
- Archive behavior stays local and deterministic through the existing daily
  report archive path conventions.
- Email behavior remains provider-neutral. The current CLI wiring uses the
  console email provider for local delivery output; no Gmail integration is
  implemented.

## v1.0 Readiness

- Daily reports are complete for v1.0 as a manual, local CLI workflow.
- ParakeetNest does not install cron, launchd, APScheduler, Celery, background
  jobs, queues, retries, or a cloud scheduler.
- Gmail delivery and cloud cron/deployment are post-v1.0 extensions.
- The flow remains advisory research only and does not place trades, execute
  orders, or automate brokerage activity.
