# Epic 23.2 - Portfolio Provider Interface

## Goal

Define a provider-neutral portfolio data source interface that allows Project
ParakeetNest to retrieve account snapshots without coupling the portfolio domain
to any brokerage, API client, database, LLM, committee workflow, or trade
execution system.

## Scope

- Add a portfolio provider contract under `src/parakeetnest/portfolio/`.
- Expose `PortfolioProvider` with `list_accounts()` and `get_snapshot(account_id)`.
- Add provider-neutral portfolio provider exceptions.
- Export the new interface and exceptions from `parakeetnest.portfolio`.
- Validate the interface with a custom test provider.

## Non-Goals

- No Robinhood or brokerage integration.
- No brokerage API client.
- No database persistence.
- No LLM logic.
- No committee logic.
- No trade execution or automatic trading.

## Architecture Notes

The provider layer depends only on the completed Portfolio Domain Models from
Epic 23.1. Implementations are responsible for translating provider-specific
account, holding, cash, and error details into the shared `PortfolioSnapshot`
model and provider-neutral exception types.

`PortfolioProvider` is a structural protocol so simple adapters, mocks, and
future brokerage implementations can satisfy the interface without inheriting
from a framework base class. This keeps the v1 surface small and testable.

## Interface Summary

```python
class PortfolioProvider(Protocol):
    def list_accounts(self) -> tuple[str, ...]:
        ...

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        ...
```

Provider exceptions:

- `PortfolioProviderError`
- `PortfolioAccountNotFoundError`
- `PortfolioDataUnavailableError`

## Validation Checklist

- [x] Portfolio provider abstractions live under `src/parakeetnest/portfolio/`.
- [x] The provider contract returns `PortfolioSnapshot`.
- [x] Account discovery returns `tuple[str, ...]`.
- [x] Errors are provider-neutral and exported from the package.
- [x] Tests cover a custom provider implementation.
- [x] Tests cover account listing, snapshot retrieval, account-not-found, and
      data-unavailable behavior.
- [x] No brokerage, persistence, LLM, committee, or trade execution logic added.
