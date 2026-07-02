# Epic 043: Robinhood Portfolio Provider

## Goal

Epic 043 replaces mock-only portfolio facts with an optional read-only
Robinhood portfolio provider while preserving the provider-neutral Portfolio
Layer.

Mock remains the default. Committee, context, and daily report code continue to
consume normalized `PortfolioSnapshot`, `PortfolioHolding`,
`PortfolioCashBalance`, and `Portfolio` models.

## Scope

Included:

- Portfolio holdings
- Cash or buying power when available
- Basic account summary totals when available

Excluded:

- Trading
- Order placement
- Options trading
- Autonomous actions
- Tax lots or realized gains
- Gmail/report delivery changes

## Configuration

Mock remains the default:

```yaml
portfolio:
  provider: mock
```

Robinhood can be selected through provider-neutral config:

```yaml
portfolio:
  provider: robinhood
  account_id: default
  robinhood_username_env_var: PARAKEETNEST_ROBINHOOD_USERNAME
  robinhood_password_env_var: PARAKEETNEST_ROBINHOOD_PASSWORD
  robinhood_session_token_env_var: PARAKEETNEST_ROBINHOOD_SESSION_TOKEN
```

Credentials and session values are read from environment variables only. No
credentials are stored in config files or committed to the repository.

For live use, install the optional read-only client dependency:

```bash
pip install "parakeetnest[robinhood]"
```

## Implementation

- `RobinhoodPortfolioProvider` implements the existing `PortfolioProvider`
  abstraction.
- `PortfolioProviderRegistry` registers `mock` and `robinhood`.
- `PortfolioConfig` selects the provider and names the environment variables to
  read.
- `create_app()` resolves the configured portfolio provider and passes only the
  provider-neutral abstraction into `PortfolioContextProvider`.
- Committee and report judgment logic do not import Robinhood code.

## Data Mapping

Robinhood holding payloads map to `PortfolioHolding`:

- symbol or ticker -> `symbol`
- quantity or shares -> `quantity`
- average buy price -> `average_cost`
- current price or market value divided by quantity -> `current_price`
- equity or market value -> `market_value`
- sector and industry -> optional classification fields

Cash or buying-power payloads map to `PortfolioCashBalance`.

Account summary payloads map to snapshot totals when available:

- equity or portfolio value -> `total_equity`
- market value or equity -> `total_market_value`
- unrealized gain/loss -> `total_unrealized_gain_loss`

If summary values are unavailable, the provider-neutral snapshot calculates
totals from holdings and cash.

## Failure Behavior

The adapter translates provider-specific failures into Portfolio Layer errors:

- missing credentials or session values -> `PortfolioDataUnavailableError`
- expired or unauthorized session -> `PortfolioDataUnavailableError`
- missing account id -> `PortfolioAccountNotFoundError`
- empty portfolio -> empty `PortfolioSnapshot`
- provider/client exception -> `PortfolioDataUnavailableError`

## Testing

Tests use fake clients only. They do not make real Robinhood network calls.

Coverage includes:

- mock default provider selection
- Robinhood provider selection via config and environment variable names
- holdings, cash, and summary mapping into provider-neutral models
- missing credentials
- expired session
- empty portfolio
- missing account
- generic client exception
- daily/app paths continuing to work with mock defaults
- architecture boundary isolation for Robinhood code

Validation:

```bash
python -m pytest
```

## Completion Checklist

- Mock remains default.
- Robinhood is selected only through `portfolio.provider = "robinhood"`.
- Robinhood provider implements the existing `PortfolioProvider` interface.
- No committee or report judgment logic changed.
- No trading, order, options, or autonomous action APIs were introduced.
- No credentials were committed.
