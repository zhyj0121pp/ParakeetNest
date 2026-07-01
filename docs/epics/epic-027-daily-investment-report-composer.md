# Epic 27 - Daily Investment Report Composer

## Goal

Compose the daily investment report body by connecting existing research
generation and plain-text rendering.

## Scope

- Add `DailyInvestmentReportComposer` under
  `src/parakeetnest/research/composer.py`.
- Input is requested tickers plus optional `account_id`, `as_of_date`, and
  `generated_at`.
- Output is a plain-text report body string.
- Reuse `InvestmentResearchService` for report assembly.
- Reuse `InvestmentResearchReportRenderer` for body rendering.

## Out of Scope

- Sending email.
- Scheduling.
- CLI additions.
- Automatic trading.
- External API calls, API keys, persistence, or new database tables.

## Composition Contract

`DailyInvestmentReportComposer.compose(...)` generates an
`InvestmentResearchReport` through the research service and renders it through
the report renderer. The composer does not assemble research facts, format
report sections, fetch provider data, persist anything, or trigger delivery.

`DailyInvestmentReportComposer.compose_report(...)` exposes the generated report
for callers that need to inspect or test the intermediate payload before
rendering.

## Acceptance Criteria

- Composer can generate an `InvestmentResearchReport` and render it into plain
  text.
- Composer keeps provider-neutral boundaries by depending only on service and
  renderer protocols.
- Tests verify orchestration between research service and renderer.
- Tests verify `account_id`, `as_of_date`, and `generated_at` are passed through.
- No email sender, scheduler, CLI, provider dependency, or database table is
  added.
