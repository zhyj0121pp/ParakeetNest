# Epic 23.4 - Portfolio Service

## Goal

Create the application-level portfolio intelligence entry point that turns
provider-neutral portfolio snapshots into deterministic portfolio summaries.

## Scope

- Add `PortfolioService` under `src/parakeetnest/portfolio/`.
- Delegate account listing and raw snapshot loading to `PortfolioProvider`.
- Expose account symbols, total equity, symbol allocation, sector allocation,
  top holdings, and a simple portfolio risk summary.
- Export `PortfolioService` from `parakeetnest.portfolio`.
- Cover service behavior, empty snapshots, invalid inputs, and provider error
  propagation with tests.

## Non-Goals

- No Robinhood integration.
- No brokerage API.
- No live market data.
- No database persistence.
- No LLM.
- No committee orchestration.
- No recommendation engine.
- No trade execution.

## Architecture Notes

`PortfolioService` sits above the portfolio provider contract. Providers own raw
data retrieval and account availability. The service owns deterministic
portfolio calculations over `PortfolioSnapshot` instances.

The service uses `Decimal` for money and percentage calculations. It does not
fetch live prices, mutate snapshots, persist results, or add provider-specific
schema assumptions.

Sector allocation groups missing sector metadata under `Unknown`. Top holdings
are sorted by market value descending with symbol as a stable tie breaker.

## Service API Summary

- `list_accounts() -> tuple[str, ...]`
- `get_snapshot(account_id: str) -> PortfolioSnapshot`
- `get_symbols(account_id: str) -> tuple[str, ...]`
- `get_total_equity(account_id: str) -> Decimal`
- `get_allocation_by_symbol(account_id: str) -> tuple[PortfolioAllocation, ...]`
- `get_allocation_by_sector(account_id: str) -> tuple[PortfolioAllocation, ...]`
- `get_top_holdings(account_id: str, limit: int = 5) -> tuple[PortfolioHolding, ...]`
- `get_risk_summary(account_id: str) -> PortfolioRiskSummary`

## Risk Summary Definition

The v1 risk summary is intentionally simple:

- `holding_count`: number of holdings in the snapshot.
- `largest_holding_symbol`: symbol of the largest holding by market value.
- `largest_holding_weight`: largest holding market value divided by total equity.
- `top_5_concentration`: combined weight of the five largest holdings.
- `cash_weight`: cash divided by total equity.
- `sector_count`: count of distinct holding sectors, grouping missing sectors as
  `Unknown`.

For compatibility with the existing domain model, `largest_position_symbol`,
`largest_position_weight`, and `concentration_score` are also populated from the
same simple concentration metrics.

## Validation Checklist

- [x] `PortfolioService` delegates account listing to `PortfolioProvider`.
- [x] `PortfolioService` delegates raw snapshot loading to `PortfolioProvider`.
- [x] Symbols are returned from snapshot holdings.
- [x] Total equity is returned as `Decimal`.
- [x] Symbol allocations use market value over total equity.
- [x] Sector allocations group missing sectors as `Unknown`.
- [x] Top holdings sort by market value descending.
- [x] Top holdings respect `limit`.
- [x] Invalid top-holdings limits raise `ValueError`.
- [x] Non-empty portfolios return simple risk summary metrics.
- [x] Empty portfolios return empty allocations and a zero risk summary.
- [x] Provider errors propagate through the service.
