# Epic 23.1: Portfolio Domain Models

## Goal

Create the foundational domain vocabulary for Phase VI Portfolio Intelligence.
The portfolio layer should let ParakeetNest represent account snapshots,
holdings, cash, allocation, exposure, and compact risk context before any
brokerage integration or committee orchestration is introduced.

## Scope

This epic adds a new `parakeetnest.portfolio` package with immutable,
provider-neutral domain models:

- `PortfolioHolding`
- `PortfolioSnapshot`
- `PortfolioPositionType`
- `PortfolioAssetType`
- `PortfolioCashBalance`
- `PortfolioAllocation`
- `PortfolioExposure`
- `PortfolioRiskSummary`

The models support basic normalization and minimal helper behavior such as
snapshot symbol listing, holding counts, empty snapshot checks, and holding
weight calculation.

## Non-Goals

This epic intentionally does not implement:

- Robinhood integration;
- real brokerage APIs;
- trade execution or automatic trading;
- a recommendation engine;
- database persistence;
- committee orchestration;
- provider-specific schema mapping.

## Architecture Notes

Portfolio domain models live in `src/parakeetnest/portfolio/` and depend only on
the Python standard library. They do not import providers, data sources, LLM
code, committee runtime code, persistence, or external APIs.

The models are frozen dataclasses with enum-backed fields. Collections are
normalized to tuples so snapshots can be passed safely between future portfolio
services, context providers, and committee memory flows without introducing
mutable shared state.

The calculations included here are deliberately small and mechanical:

- holding market value;
- holding unrealized gain/loss;
- holding unrealized gain/loss percent;
- snapshot market value, cash, equity, and unrealized gain/loss totals.

Richer business logic such as risk scoring, rebalancing, tax treatment,
portfolio optimization, and recommendation generation belongs in later epics.

## Domain Model Summary

`PortfolioHolding` represents one position at a point in time. It includes
symbol, name, quantity, average cost, current price, market value, unrealized
gain/loss, asset type, position type, optional sector and industry, and
currency.

`PortfolioSnapshot` represents one account at a point in time. It includes
account id, timestamp, holdings, cash balances, total market value, total cash,
total equity, total unrealized gain/loss, and unrealized gain/loss percent.

`PortfolioCashBalance` represents cash in one currency.

`PortfolioAllocation` and `PortfolioExposure` provide provider-neutral summary
shapes for future allocation and exposure features.

`PortfolioRiskSummary` provides a compact, provider-neutral risk summary shape
for future portfolio context rendering.

## Validation Checklist

- [x] New `parakeetnest.portfolio` package added.
- [x] Public models exported from `parakeetnest.portfolio`.
- [x] Domain models are immutable frozen dataclasses.
- [x] Domain models avoid provider, data source, LLM, committee runtime,
      persistence, and external API dependencies.
- [x] Holding creation is covered by tests.
- [x] Market value calculation is covered by tests.
- [x] Gain/loss calculation is covered by tests.
- [x] Portfolio totals are covered by tests.
- [x] Empty portfolio behavior is covered by tests.
- [x] Portfolio weight calculation is covered by tests.
- [x] Long equity holding behavior is covered by tests.
- [x] Cash balance handling is covered by tests.
