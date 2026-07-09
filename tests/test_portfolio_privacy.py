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
