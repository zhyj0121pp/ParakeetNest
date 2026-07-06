"""Tests for provider-neutral position context construction."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, fields
from datetime import date

import pytest

from parakeetnest.context import (
    KnowledgeBaseSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    NewsContext,
    NewsItem,
    PortfolioPosition,
    ValuationContextItem,
    ValuationContextSnapshot,
)
from parakeetnest.decision import PositionContext
from parakeetnest.services import PositionContextBuilder


@dataclass(frozen=True)
class ProviderNeutralPosition:
    symbol: str
    name: str
    quantity: float
    market_value: float
    weight: float


def test_position_context_has_required_field_boundary() -> None:
    """PositionContext should expose the Phase II context fields."""
    assert tuple(field.name for field in fields(PositionContext)) == (
        "symbol",
        "company_name",
        "quantity",
        "market_value",
        "portfolio_weight",
        "cost_basis",
        "unrealized_gain_loss",
        "current_price",
        "recent_price_change",
        "relevant_news",
        "relevant_research",
        "risk_notes",
        "valuation_notes",
        "momentum_notes",
        "portfolio_notes",
    )


def test_position_context_construction_normalizes_values() -> None:
    """PositionContext should normalize identity, numbers, and text collections."""
    context = PositionContext(
        symbol=" nvda ",
        company_name=" NVIDIA Corporation ",
        quantity=2,
        market_value=1840,
        portfolio_weight=0.25,
        cost_basis=820,
        unrealized_gain_loss=200,
        current_price=920,
        recent_price_change=0.03,
        relevant_news=[" Blackwell demand remains strong. ", ""],  # type: ignore[arg-type]
        relevant_research=[" Thesis intact. "],  # type: ignore[arg-type]
        risk_notes=[" Valuation risk. "],  # type: ignore[arg-type]
        valuation_notes=[" Premium multiple. "],  # type: ignore[arg-type]
        momentum_notes=[" Positive trend. "],  # type: ignore[arg-type]
        portfolio_notes=[" Largest holding. "],  # type: ignore[arg-type]
    )

    assert context.symbol == "NVDA"
    assert context.company_name == "NVIDIA Corporation"
    assert context.quantity == 2.0
    assert context.market_value == 1840.0
    assert context.portfolio_weight == 0.25
    assert context.relevant_news == ("Blackwell demand remains strong.",)
    assert context.risk_notes == ("Valuation risk.",)

    with pytest.raises(FrozenInstanceError):
        context.symbol = "AMD"


def test_position_context_optional_fields_can_be_absent() -> None:
    """Optional market and cost fields should default to None."""
    context = PositionContext(
        symbol="MSFT",
        company_name="Microsoft",
        quantity=1,
        market_value=500,
        portfolio_weight=0.1,
    )

    assert context.cost_basis is None
    assert context.unrealized_gain_loss is None
    assert context.current_price is None
    assert context.recent_price_change is None
    assert context.relevant_news == ()
    assert context.relevant_research == ()


def test_position_context_builder_maps_available_context() -> None:
    """Builder should select symbol-matched context without fetching data."""
    position = PortfolioPosition(
        symbol=" amd ",
        name=" Advanced Micro Devices ",
        quantity=10,
        market_value=1500,
        cost_basis=1200,
        unrealized_pl=300,
        weight=0.15,
    )
    market = MarketSnapshot(
        source="market_context",
        points=(
            MarketDataPoint(symbol="NVDA", source="market_context", price=900),
            MarketDataPoint(
                symbol="AMD",
                source="market_context",
                price=150,
                daily_change_percent=0.025,
            ),
        ),
    )
    news = NewsContext(
        source="news_context",
        items=(
            NewsItem(
                symbol="AMD",
                title="AMD launches new accelerator",
                source="news_context",
                summary="Management highlighted data center demand.",
            ),
            NewsItem(symbol="NVDA", title="NVIDIA update", source="news_context"),
        ),
    )
    valuation = ValuationContextSnapshot(
        source="valuation_context",
        items=(
            ValuationContextItem(
                symbol="AMD",
                as_of_date=date(2026, 7, 6),
                calculation_notes=("P/S ratio is above history.",),
            ),
        ),
    )
    knowledge_base = KnowledgeBaseSnapshot(
        research_notes=("AMD thesis: AI accelerator share gains remain possible.",),
        lessons_learned=("MSFT lesson: avoid unrelated research leakage.",),
    )

    context = PositionContextBuilder().build(
        position,
        market=market,
        news=news,
        valuation=valuation,
        knowledge_base=knowledge_base,
        risk_notes=("Execution risk remains material.",),
        valuation_notes=("Compare multiple to peers.",),
        momentum_notes=("Price trend improved.",),
        portfolio_notes=("Position is mid-sized.",),
    )

    assert context.symbol == "AMD"
    assert context.company_name == "Advanced Micro Devices"
    assert context.quantity == 10.0
    assert context.market_value == 1500.0
    assert context.portfolio_weight == 0.15
    assert context.cost_basis == 1200.0
    assert context.unrealized_gain_loss == 300.0
    assert context.current_price == 150.0
    assert context.recent_price_change == 0.025
    assert context.relevant_news == (
        "AMD launches new accelerator - Management highlighted data center demand.",
    )
    assert context.relevant_research == (
        "AMD thesis: AI accelerator share gains remain possible.",
    )
    assert context.valuation_notes == (
        "P/S ratio is above history.",
        "Compare multiple to peers.",
    )
    assert context.risk_notes == ("Execution risk remains material.",)
    assert context.momentum_notes == ("Price trend improved.",)
    assert context.portfolio_notes == ("Position is mid-sized.",)


def test_position_context_builder_accepts_plain_provider_neutral_objects() -> None:
    """Builder should not require provider-specific portfolio objects."""
    position = ProviderNeutralPosition(
        symbol="msft",
        name="Microsoft",
        quantity=2,
        market_value=1000,
        weight=0.2,
    )

    context = PositionContextBuilder().build(position)

    assert context.symbol == "MSFT"
    assert context.company_name == "Microsoft"
    assert context.quantity == 2.0
    assert context.market_value == 1000.0
    assert context.portfolio_weight == 0.2
    assert "robinhood" not in repr(context).lower()
    assert "yahoo" not in repr(context).lower()
    assert "gmail" not in repr(context).lower()
