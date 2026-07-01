# Epic 23.3 - Mock Portfolio Provider

## Goal

Create a deterministic portfolio provider for local development, testing, and
future portfolio committee workflows.

## Scope

- Add `MockPortfolioProvider` under `src/parakeetnest/portfolio/`.
- Implement the `PortfolioProvider` contract with `list_accounts()` and
  `get_snapshot(account_id)`.
- Provide deterministic default account data when no snapshots are passed.
- Allow custom snapshots, including an explicitly empty snapshot mapping.
- Export the provider from `parakeetnest.portfolio`.
- Cover default, custom, empty, and missing-account behavior with tests.

## Non-Goals

- No Robinhood integration.
- No brokerage API.
- No live market data.
- No database persistence.
- No portfolio analysis logic.
- No committee orchestration.
- No recommendation engine.
- No trade execution.

## Architecture Notes

`MockPortfolioProvider` is an in-memory adapter over `PortfolioSnapshot`
instances. It depends only on the portfolio domain models and provider-neutral
portfolio exceptions.

The constructor treats `None` as a request for embedded default fixtures. Passing
an explicit mapping uses exactly that mapping, so `{}` creates a valid empty
provider. This keeps local tests deterministic while allowing future committee
workflows to inject custom portfolio scenarios.

The default data uses a fixed timestamp and fixed prices. It does not use random
values, live market data, external APIs, persistence, or brokerage-specific
schemas.

## Default Mock Account Summary

Default account id: `mock-main`

Default holdings:

- `NVDA` - Technology, Semiconductors
- `MSFT` - Technology, Software - Infrastructure
- `AAPL` - Technology, Consumer Electronics
- `MU` - Technology, Semiconductors
- `CRDO` - Technology, Communication Equipment
- `RKLB` - Industrials, Aerospace & Defense
- `OKLO` - Utilities, Utilities - Renewable

The account also includes a USD cash balance.

## Validation Checklist

- [x] `MockPortfolioProvider` implements `PortfolioProvider`.
- [x] Default provider lists `mock-main`.
- [x] Default provider returns a non-empty `PortfolioSnapshot`.
- [x] Default holdings include the expected symbols.
- [x] Custom snapshots override defaults.
- [x] Explicitly empty snapshots are supported.
- [x] Unknown account ids raise `PortfolioAccountNotFoundError`.
- [x] Provider is deterministic and uses no random data.
- [x] Provider uses no live market data, external APIs, persistence, analysis,
      committee orchestration, recommendation, or trade execution logic.
