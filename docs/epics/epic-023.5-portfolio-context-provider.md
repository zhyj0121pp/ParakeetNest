# Epic 23.5: Portfolio Context Provider

## Goal

Expose portfolio intelligence through the existing Context Layer so future
committee agents can consume read-only portfolio state before reasoning.

The committee remembers before it reasons: portfolio context is assembled as
structured context first, then rendered into prompt-ready Markdown by the
Context Layer renderer.

## Scope

- Add `PortfolioContextProvider` under `parakeetnest.portfolio`.
- Adapt `PortfolioService` outputs into `MeetingContext.portfolio`.
- Include account identity, portfolio totals, holding count, symbols, top
  holdings, allocation by symbol, allocation by sector, and portfolio risk
  summary.
- Render portfolio context in human-readable committee sections:
  - Portfolio Summary
  - Top Holdings
  - Symbol Allocation
  - Sector Allocation
  - Risk Summary
- Keep provider behavior deterministic, read-only, and provider-neutral.

## Non-Goals

- No recommendation logic.
- No buy, sell, or hold decisions.
- No automatic trading or trade execution.
- No Robinhood or brokerage integration.
- No database persistence.
- No LLM calls.
- No committee orchestration changes.

## Architecture Notes

`PortfolioContextProvider` depends on `PortfolioService`, not on concrete
brokerage providers. The provider accepts an `account_id` at construction time
and uses the service boundary to read:

- the account snapshot;
- top holdings;
- symbol allocations;
- sector allocations;
- risk summary.

The provider contributes a partial `MeetingContext` with
`MeetingContext.portfolio` populated. Context assembly still follows the
existing first-provider-wins merge behavior in `ContextService`.

Unsupported requests raise `UnsupportedContextRequestError`, matching the
Context Layer convention. Portfolio provider and service failures are not
swallowed by this adapter; they propagate as provider-neutral portfolio errors,
matching the current service-backed provider style.

## Context Output Summary

The enriched portfolio context includes:

- `account_id`
- `total_equity`
- `total_market_value`
- `total_cash`
- `holding_count`
- `symbols`
- `top_holdings`
- `allocation_by_symbol`
- `allocation_by_sector`
- `risk_summary`

The renderer presents these fields under the Portfolio section with clear
subsections suitable for Xixi, Dongdong, Yoyo, the Chairman, and the Investment
Secretary.

## Validation Checklist

- [x] `PortfolioContextProvider` can be created with `PortfolioService` and an
  account id.
- [x] Generated context includes a portfolio summary.
- [x] Generated context includes top holdings.
- [x] Generated context includes sector allocation.
- [x] Generated context includes risk summary.
- [x] Empty portfolios render safely.
- [x] Provider errors follow existing Context Layer conventions.
- [x] Rendered context does not include recommendation language.
- [x] No trading, brokerage, persistence, LLM, or committee orchestration logic
  was added.
- [ ] `pytest` passes in an environment with test dependencies installed.
