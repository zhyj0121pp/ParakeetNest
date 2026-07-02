"""Tests for Portfolio Intelligence domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime

import pytest

from parakeetnest.portfolio import (
    Holding,
    Portfolio,
    PortfolioAllocation,
    PortfolioAssetType,
    PortfolioCashBalance,
    PortfolioExposure,
    PortfolioHolding,
    PortfolioPositionType,
    PortfolioRiskSummary,
    PortfolioSnapshot,
)


AS_OF = datetime(2026, 7, 1, 13, 30, tzinfo=UTC)


def test_holding_model_has_story_39_1_field_boundary() -> None:
    """Holding should expose only the provider-neutral portfolio fields."""
    assert tuple(field.name for field in fields(Holding)) == (
        "ticker",
        "quantity",
        "market_value",
        "portfolio_weight",
        "average_cost",
        "unrealized_gain_loss",
    )


def test_holding_normalizes_minimal_provider_neutral_values() -> None:
    """Minimal holdings should normalize broker-neutral values."""
    holding = Holding(
        ticker=" nvda ",
        quantity=3,
        market_value=600,
        portfolio_weight=0.25,
        average_cost=150,
        unrealized_gain_loss=150,
    )

    assert holding.ticker == "NVDA"
    assert holding.quantity == 3.0
    assert holding.market_value == 600.0
    assert holding.portfolio_weight == 0.25
    assert holding.average_cost == 150.0
    assert holding.unrealized_gain_loss == 150.0

    with pytest.raises(FrozenInstanceError):
        holding.ticker = "AMD"


def test_holding_optional_fields_default_to_none() -> None:
    """Cost and gain/loss should be optional at the provider boundary."""
    holding = Holding(
        ticker="MSFT",
        quantity=2,
        market_value=1000,
        portfolio_weight=0.4,
    )

    assert holding.average_cost is None
    assert holding.unrealized_gain_loss is None


def test_portfolio_model_has_story_39_1_field_boundary() -> None:
    """Portfolio should expose only the minimal portfolio architecture fields."""
    assert tuple(field.name for field in fields(Portfolio)) == (
        "cash_balance",
        "total_market_value",
        "holdings",
    )


def test_portfolio_normalizes_holdings_and_tickers() -> None:
    """Portfolios should keep holdings immutable and provider-neutral."""
    nvda = Holding(
        ticker="nvda",
        quantity=1,
        market_value=200,
        portfolio_weight=0.2,
    )
    portfolio = Portfolio(
        cash_balance=500,
        total_market_value=1000,
        holdings=[nvda],
    )

    assert portfolio.cash_balance == 500.0
    assert portfolio.total_market_value == 1000.0
    assert portfolio.holdings == (nvda,)
    assert portfolio.tickers() == ("NVDA",)

    with pytest.raises(FrozenInstanceError):
        portfolio.cash_balance = 0


def test_portfolio_asset_type_values_are_stable() -> None:
    """Asset types should describe asset classes, not providers."""
    assert PortfolioAssetType.EQUITY.value == "equity"
    assert PortfolioAssetType.ETF.value == "etf"
    assert PortfolioAssetType.MUTUAL_FUND.value == "mutual_fund"
    assert PortfolioAssetType.OPTION.value == "option"
    assert PortfolioAssetType.BOND.value == "bond"
    assert PortfolioAssetType.CASH.value == "cash"
    assert PortfolioAssetType.CRYPTO.value == "crypto"
    assert PortfolioAssetType.OTHER.value == "other"


def test_portfolio_position_type_values_are_stable() -> None:
    """Position types should represent direction without execution semantics."""
    assert PortfolioPositionType.LONG.value == "long"
    assert PortfolioPositionType.SHORT.value == "short"


def test_creating_holding_normalizes_fields_and_calculates_values() -> None:
    """A holding should calculate value and unrealized gain/loss by default."""
    holding = PortfolioHolding(
        symbol=" nvda ",
        name=" NVIDIA Corporation ",
        quantity=10,
        average_cost=100.0,
        current_price=125.0,
        asset_type="equity",
        position_type="long",
        sector=" Technology ",
        industry=" Semiconductors ",
        currency=" usd ",
    )

    assert holding.symbol == "NVDA"
    assert holding.name == "NVIDIA Corporation"
    assert holding.quantity == 10.0
    assert holding.average_cost == 100.0
    assert holding.current_price == 125.0
    assert holding.market_value == 1250.0
    assert holding.unrealized_gain_loss == 250.0
    assert holding.unrealized_gain_loss_percent == 0.25
    assert holding.asset_type is PortfolioAssetType.EQUITY
    assert holding.position_type is PortfolioPositionType.LONG
    assert holding.sector == "Technology"
    assert holding.industry == "Semiconductors"
    assert holding.currency == "USD"

    with pytest.raises(FrozenInstanceError):
        holding.symbol = "AMD"


def test_holding_accepts_explicit_point_in_time_values() -> None:
    """Imported snapshots may provide explicit provider-neutral values."""
    holding = PortfolioHolding(
        symbol="MSFT",
        name="Microsoft",
        quantity=2,
        average_cost=300.0,
        current_price=350.0,
        market_value=701.0,
        unrealized_gain_loss=101.0,
        unrealized_gain_loss_percent=0.1683,
    )

    assert holding.market_value == 701.0
    assert holding.unrealized_gain_loss == 101.0
    assert holding.unrealized_gain_loss_percent == 0.1683


def test_long_equity_holding_defaults_to_usd_equity_long() -> None:
    """The common v1 holding case should be concise to construct."""
    holding = PortfolioHolding(
        symbol="AAPL",
        name="Apple Inc.",
        quantity=5,
        average_cost=180.0,
        current_price=200.0,
    )

    assert holding.asset_type is PortfolioAssetType.EQUITY
    assert holding.position_type is PortfolioPositionType.LONG
    assert holding.currency == "USD"
    assert holding.market_value == 1000.0


def test_portfolio_snapshot_calculates_totals_and_helpers() -> None:
    """Snapshot totals should aggregate holdings and cash balances."""
    nvda = PortfolioHolding(
        symbol="NVDA",
        name="NVIDIA Corporation",
        quantity=10,
        average_cost=100.0,
        current_price=125.0,
    )
    msft = PortfolioHolding(
        symbol="MSFT",
        name="Microsoft",
        quantity=2,
        average_cost=300.0,
        current_price=350.0,
    )
    snapshot = PortfolioSnapshot(
        account_id=" taxable ",
        as_of=AS_OF,
        holdings=[nvda, msft],
        cash_balances=[PortfolioCashBalance(amount=500.0)],
    )

    assert snapshot.account_id == "taxable"
    assert snapshot.holdings == (nvda, msft)
    assert snapshot.cash_balances == (PortfolioCashBalance(amount=500.0),)
    assert snapshot.total_market_value == 1950.0
    assert snapshot.total_cash == 500.0
    assert snapshot.total_equity == 2450.0
    assert snapshot.total_unrealized_gain_loss == 350.0
    assert snapshot.total_unrealized_gain_loss_percent == pytest.approx(350.0 / 1600.0)
    assert snapshot.symbols() == ("NVDA", "MSFT")
    assert snapshot.holding_count() == 2
    assert snapshot.is_empty() is False


def test_empty_portfolio_behavior() -> None:
    """Empty snapshots should expose zero totals and no symbols."""
    snapshot = PortfolioSnapshot(account_id="paper", as_of=AS_OF)

    assert snapshot.holdings == ()
    assert snapshot.cash_balances == ()
    assert snapshot.total_market_value == 0.0
    assert snapshot.total_cash == 0.0
    assert snapshot.total_equity == 0.0
    assert snapshot.total_unrealized_gain_loss == 0.0
    assert snapshot.total_unrealized_gain_loss_percent == 0.0
    assert snapshot.symbols() == ()
    assert snapshot.holding_count() == 0
    assert snapshot.is_empty() is True


def test_portfolio_weight_calculation() -> None:
    """Holdings should calculate weight without owning allocation policy."""
    holding = PortfolioHolding(
        symbol="NVDA",
        name="NVIDIA Corporation",
        quantity=4,
        average_cost=100.0,
        current_price=125.0,
    )

    assert holding.weight_in_portfolio(2000.0) == 0.25
    assert holding.weight_in_portfolio(0.0) == 0.0


def test_cash_balance_handling() -> None:
    """Cash balances should normalize currency and contribute to equity."""
    usd_cash = PortfolioCashBalance(amount=1000, currency=" usd ")
    eur_cash = PortfolioCashBalance(amount=250, currency=" eur ")
    snapshot = PortfolioSnapshot(
        account_id="ira",
        as_of=AS_OF,
        cash_balances=[usd_cash, eur_cash],
    )

    assert usd_cash.amount == 1000.0
    assert usd_cash.currency == "USD"
    assert eur_cash.currency == "EUR"
    assert snapshot.total_cash == 1250.0
    assert snapshot.total_equity == 1250.0
    assert snapshot.is_empty() is False


def test_supporting_portfolio_models_are_immutable_and_normalized() -> None:
    """Supporting models should be compact and provider-neutral."""
    allocation = PortfolioAllocation(category=" sector:technology ", value=1500, percent=0.6)
    exposure = PortfolioExposure(name=" mega cap ", market_value=1200, percent=0.48)
    risk_summary = PortfolioRiskSummary(
        concentration_score=0.72,
        largest_position_symbol=" nvda ",
        largest_position_weight=0.35,
        cash_weight=0.10,
        notes=(" high single-name exposure ", ""),
    )

    assert allocation.category == "sector:technology"
    assert allocation.value == 1500.0
    assert allocation.percent == 0.6
    assert exposure.name == "mega cap"
    assert exposure.market_value == 1200.0
    assert exposure.percent == 0.48
    assert risk_summary.largest_position_symbol == "NVDA"
    assert risk_summary.notes == ("high single-name exposure",)

    with pytest.raises(FrozenInstanceError):
        risk_summary.cash_weight = 0.2


def test_public_models_are_exported_from_portfolio_package() -> None:
    """The package should expose the public Portfolio Intelligence model surface."""
    import parakeetnest.portfolio as portfolio

    assert portfolio.PortfolioHolding is PortfolioHolding
    assert portfolio.Holding is Holding
    assert portfolio.Portfolio is Portfolio
    assert portfolio.PortfolioSnapshot is PortfolioSnapshot
    assert portfolio.PortfolioPositionType is PortfolioPositionType
    assert portfolio.PortfolioAssetType is PortfolioAssetType
    assert portfolio.PortfolioCashBalance is PortfolioCashBalance
    assert portfolio.PortfolioAllocation is PortfolioAllocation
    assert portfolio.PortfolioExposure is PortfolioExposure
    assert portfolio.PortfolioRiskSummary is PortfolioRiskSummary


def test_invalid_enum_values_are_rejected() -> None:
    """Unknown enum strings should fail at the portfolio domain boundary."""
    with pytest.raises(ValueError):
        PortfolioHolding(
            symbol="NVDA",
            name="NVIDIA Corporation",
            quantity=1,
            average_cost=100.0,
            current_price=125.0,
            asset_type="brokerage_special",
        )

    with pytest.raises(ValueError):
        PortfolioHolding(
            symbol="NVDA",
            name="NVIDIA Corporation",
            quantity=1,
            average_cost=100.0,
            current_price=125.0,
            position_type="covered_call",
        )
