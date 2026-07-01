# Epic 020: First Complete Investment Committee

Status: Epic 20.1 - Product Skeleton Completed

## Purpose

Create the product skeleton for the first complete AI investment committee
without wiring full end-to-end meeting execution.

The committee remembers before it reasons. Epic 20.1 defines the request,
report, decision, and composition contracts that future execution work can use
without changing the frozen v2.0 architecture.

## Scope

Epic 20.1 adds data-only committee product models:

- `InvestmentCommitteeRequest` captures ticker, topic, time horizon, optional
  user question, and optional portfolio/context notes.
- `InvestmentCommitteeReport` captures macro, sector, fundamental, valuation,
  risk, momentum/sentiment, bull case, bear case, key risks, decision,
  confidence, and recommended action.
- `InvestmentCommitteeDecision` defines `BUY`, `HOLD`, `WATCH`, and `AVOID`.
- `DEFAULT_INVESTMENT_COMMITTEE` defines the default complete committee
  composition.

## Default Composition

The default committee roles are:

- Macro Strategist
- Sector Analyst
- Fundamental Analyst
- Valuation Analyst
- Risk Manager
- Momentum / Sentiment Analyst
- Chair / CIO

The composition is metadata only in this epic. It does not instantiate new
agent runtime behavior.

## Architecture

Epic 20.1 stays inside the committee domain model boundary:

```text
committee product request/report models -> future meeting execution
```

No data providers, signal services, or external APIs are introduced. The
committee runtime and `MeetingService` remain unchanged.

## Tests

Coverage proves:

- request model construction and normalization;
- report model construction and enum normalization;
- stable decision enum values;
- complete default committee composition.

The full test suite should continue to pass with:

```text
pytest
```

## Out of Scope

Epic 20.1 intentionally excludes:

- automatic trading;
- `MeetingService` wiring;
- agent runtime changes;
- new data providers;
- external API calls;
- end-to-end committee execution for the new product skeleton.
