from __future__ import annotations

from parakeetnest.context.models import PortfolioPosition, PortfolioSnapshot
from parakeetnest.portfolio import PortfolioPrivacyContextBuilder


def test_portfolio_privacy_context_builder_returns_bucketed_summary_and_positions() -> None:
    snapshot = PortfolioSnapshot(
        source="portfolio_provider",
        account_id="742192826",
        total_value=100_000,
        cash_balance=5_000,
        positions=(
            PortfolioPosition(
                symbol="NVDA",
                quantity=10,
                market_value=25_000,
                cost_basis=20_000,
                unrealized_pl=5_000,
                weight=0.25,
                sector="Technology",
            ),
            PortfolioPosition(
                symbol="AAPL",
                quantity=5,
                market_value=10_000,
                cost_basis=12_000,
                unrealized_pl=-2_000,
                weight=0.10,
                sector="Technology",
            ),
        ),
    )

    summary, positions = PortfolioPrivacyContextBuilder().build(
        snapshot,
        ("NVDA", "MSFT"),
    )

    assert summary is not None
    assert summary.privacy_level == "bucketed"
    assert summary.number_of_positions == 2
    assert summary.cash_allocation_bucket == "low"
    assert summary.concentration_level in {"moderate", "high", "very_high"}
    assert summary.largest_position_bucket == "large"
    assert summary.dominant_sector == "Technology"

    nvda = positions[0]
    assert nvda.ticker == "NVDA"
    assert nvda.is_holding is True
    assert nvda.position_size_bucket == "large"
    assert nvda.portfolio_rank_bucket == "largest"
    assert nvda.unrealized_return_bucket == "gain"
    assert nvda.add_allowed is False
    assert nvda.privacy_level == "bucketed"

    msft = positions[1]
    assert msft.ticker == "MSFT"
    assert msft.is_holding is False
    assert msft.position_size_bucket == "none"
    assert msft.portfolio_rank_bucket == "not_holding"

    rendered = f"{summary} {positions}"
    forbidden = (
        "742192826",
        "market_value",
        "cost_basis",
        "quantity",
        "unrealized_pl",
        "25000",
        "20000",
        "5000",
        "0.25",
    )
    assert all(term not in rendered for term in forbidden)


def test_high_concentration_alone_does_not_mark_every_small_holding_for_trim() -> None:
    snapshot = PortfolioSnapshot(
        source="portfolio_provider",
        total_value=100_000,
        cash_balance=10_000,
        positions=(
            _position("CORE", weight=0.35),
            _position("MID", weight=0.12),
            _position("SMALL", weight=0.04),
        ),
    )

    _, positions = PortfolioPrivacyContextBuilder().build(
        snapshot,
        ("CORE", "MID", "SMALL"),
    )
    by_ticker = {context.ticker: context for context in positions}

    assert by_ticker["CORE"].trim_candidate is True
    assert by_ticker["MID"].trim_candidate is True
    assert by_ticker["SMALL"].position_size_bucket == "small"
    assert by_ticker["SMALL"].portfolio_rank_bucket == "top_3"
    assert by_ticker["SMALL"].trim_candidate is True

    snapshot_with_outside_top3_small = PortfolioSnapshot(
        source="portfolio_provider",
        total_value=100_000,
        cash_balance=10_000,
        positions=(
            _position("CORE", weight=0.35),
            _position("MID", weight=0.12),
            _position("THIRD", weight=0.10),
            _position("SMALL", weight=0.04),
        ),
    )
    _, positions = PortfolioPrivacyContextBuilder().build(
        snapshot_with_outside_top3_small,
        ("SMALL",),
    )

    assert positions[0].portfolio_rank_bucket == "top_5"
    assert positions[0].trim_candidate is False


def test_very_low_cash_makes_add_not_allowed() -> None:
    snapshot = PortfolioSnapshot(
        source="portfolio_provider",
        total_value=100_000,
        cash_balance=1_000,
        positions=(_position("SMALL", weight=0.04),),
    )

    _, positions = PortfolioPrivacyContextBuilder().build(snapshot, ("SMALL", "NEW"))

    assert positions[0].add_allowed is False
    assert positions[1].is_holding is False
    assert positions[1].add_allowed is False


def test_large_position_is_trim_candidate() -> None:
    snapshot = PortfolioSnapshot(
        source="portfolio_provider",
        total_value=100_000,
        cash_balance=10_000,
        positions=(_position("LARGE", weight=0.22),),
    )

    _, positions = PortfolioPrivacyContextBuilder().build(snapshot, ("LARGE",))

    assert positions[0].position_size_bucket == "large"
    assert positions[0].trim_candidate is True
    assert positions[0].add_allowed is False


def test_large_loss_medium_position_is_trim_candidate() -> None:
    snapshot = PortfolioSnapshot(
        source="portfolio_provider",
        total_value=100_000,
        cash_balance=10_000,
        positions=(
            _position(
                "LOSS",
                weight=0.12,
                cost_basis=20_000,
                unrealized_pl=-7_000,
            ),
        ),
    )

    _, positions = PortfolioPrivacyContextBuilder().build(snapshot, ("LOSS",))

    assert positions[0].position_size_bucket == "medium"
    assert positions[0].unrealized_return_bucket == "large_loss"
    assert positions[0].trim_candidate is True


def _position(
    symbol: str,
    *,
    weight: float,
    cost_basis: float = 10_000,
    unrealized_pl: float = 0,
) -> PortfolioPosition:
    return PortfolioPosition(
        symbol=symbol,
        quantity=1,
        market_value=weight * 100_000,
        cost_basis=cost_basis,
        unrealized_pl=unrealized_pl,
        weight=weight,
        sector="Technology",
    )
