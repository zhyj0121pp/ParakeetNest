# Epic 30 - Report Scheduler

## Goal

Add a small scheduler abstraction that can trigger daily investment report
delivery without knowing how research is generated, rendered, or delivered.

## Scope

- Add provider-neutral schedule models under
  `src/parakeetnest/research/scheduler.py`.
- Support `ReportScheduleFrequency.DAILY` for v1.
- Add `ReportScheduler.run_once(schedule, generated_at=None)` as an
  in-process manual trigger.
- Pass schedule inputs into `DailyReportDeliveryService.deliver(...)` through a
  `DailyReportDeliveryRequest`.
- Return `ScheduledReportRun` with the schedule, run timestamp, run status, and
  delivery result.

## Out of Scope

- No background daemon or scheduling loop.
- No cron, APScheduler, Celery, or other scheduler dependency.
- No real email provider, credentials, or provider-specific configuration.
- No CLI and no database tables.
- No automatic trading.

## Architecture Decisions

`ReportScheduler` depends on a small delivery-service protocol with the same
shape as `DailyReportDeliveryService.deliver(...)`. The scheduler only knows
when a schedule is manually triggered and which use case to call.

`ReportSchedule` stores cadence and delivery inputs: tickers, recipient email,
optional account ID, optional time of day, optional timezone string, and
metadata. The `time_of_day` and `timezone` fields are stored for future daemon
or cron integration but are not interpreted by the manual trigger.

Delivery failures remain provider-neutral. If the daily delivery use case
returns a failed `ReportDeliveryResult`, the scheduled run is marked
`ScheduledReportRunStatus.FAILED` and carries the original delivery result.

## Acceptance Criteria

- Can create a daily report schedule.
- Can manually trigger one scheduled run.
- Scheduler passes `tickers`, `recipient_email`, `account_id`, `generated_at`,
  and `metadata` into `DailyReportDeliveryService`.
- Scheduler returns a scheduled run result with status and delivery result.
- Tests cover successful run and failed delivery result.
