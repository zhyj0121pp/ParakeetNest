# Epic 26 - Investment Report Renderer

## Goal

Render `InvestmentResearchReport` into a standalone interactive HTML report
that can be attached by a delivery layer.

## Scope

- Add a renderer under `src/parakeetnest/research/rendering.py`.
- Input is `InvestmentResearchReport`.
- Output is a standalone HTML string suitable for an attachment.
- Include header, executive summary, ticker reports, recommendations, risks,
  catalysts, and evidence notes.
- Keep the renderer provider-neutral.

## Out of Scope

- Sending email.
- Scheduling.
- Automatic trading.
- Provider calls, API keys, persistence, or new database tables.
- CLI additions unless a future workflow needs them.

## Rendering Contract

`InteractiveHtmlInvestmentResearchReportRenderer.render(report)` returns
deterministic standalone HTML with one trailing newline. It does not fetch data
or recover missing context. All investment content must already be present on
the report model.

The report is organized for a sub-five-minute read:

- `Header` identifies title, generated timestamp, and covered tickers.
- `Executive Summary` gives coverage count, action counts, and one-line ticker
  summaries.
- `Ticker Reports` gives each ticker summary, recommendation, rationale, bull
  case, bear case, findings, and source summaries.
- `Recommendations` repeats the complete recommendation contract: action,
  confidence, horizon, evidence, risks, catalysts, and optional rationale.
- `Risks` and `Catalysts` provide scan-friendly aggregate sections.
- `Evidence Notes` preserves report, ticker, finding, risk, and catalyst notes
  without coupling the renderer to any provider.

## Acceptance Criteria

- Interactive HTML renderer added for `InvestmentResearchReport`.
- Rendering tests cover required sections, recommendation contract details,
  evidence notes, and empty report behavior.
- No email sender, scheduler, CLI, provider dependency, or trading behavior.
