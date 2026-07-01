# Epic 23.8 - CLI Portfolio Committee Runner

## Goal

Add a local-development CLI entry point that runs an advisory portfolio committee
meeting against the deterministic mock portfolio account.

## Scope

- Wire `MockPortfolioProvider`, `PortfolioService`, and `PortfolioContextProvider`.
- Run portfolio committee agents through the shared `AgentRuntime`.
- Use `PortfolioCommitteeOrchestrator` as the committee entry point.
- Enable SQLite-backed committee memory by default.
- Allow memory to be disabled for isolated local runs.
- Print portfolio metadata, agent responses, and an advisory-only disclaimer.

## Non-Goals

- No Robinhood integration.
- No brokerage API integration.
- No trade execution or order placement.
- No automatic rebalancing.
- No production scheduler, daemon, or web server.

## CLI Usage

```bash
python -m parakeetnest.cli.portfolio_committee --account-id mock-main
```

Optional flags:

```bash
python -m parakeetnest.cli.portfolio_committee --account-id mock-main --no-memory
python -m parakeetnest.cli.portfolio_committee --account-id mock-main --verbose
```

## Expected Output Summary

The command prints:

- portfolio committee title
- account id
- status, committee metadata, and memory mode
- mock portfolio totals and symbols
- one response block per portfolio committee agent
- final summary when an agent provides one
- advisory-only language stating that the runner does not connect to brokerages,
  place orders, execute trades, or rebalance automatically

## Validation Checklist

- `pytest`
- `python -m parakeetnest.cli.portfolio_committee --account-id mock-main`
- Confirm output includes `Portfolio Committee Meeting`.
- Confirm output includes `account_id: mock-main`.
- Confirm output includes agent responses.
- Confirm output includes advisory-only disclaimer.
- Confirm no trading, order placement, brokerage, scheduler, daemon, or web server
  behavior was added.
