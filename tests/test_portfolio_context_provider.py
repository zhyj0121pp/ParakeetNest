"""Tests for PortfolioContextProvider provider-backed context generation."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from parakeetnest.context import (
    ContextRequest,
    ContextService,
    MeetingContextPromptRenderer,
    UnsupportedContextRequestError,
)
from parakeetnest.portfolio import (
    Portfolio,
    PortfolioCashBalance,
    PortfolioContextProvider,
    PortfolioDataUnavailableError,
    PortfolioHolding,
    PortfolioProvider,
    PortfolioSnapshot,
)


AS_OF = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


class StaticPortfolioProvider:
    """Small provider test double for context provider tests."""

    def __init__(self, snapshots: dict[str, PortfolioSnapshot]) -> None:
        self.snapshots = snapshots

    def list_accounts(self) -> tuple[str, ...]:
        return tuple(self.snapshots)

    def get_portfolio(self, account_id: str) -> Portfolio:
        snapshot = self.get_snapshot(account_id)
        return Portfolio(
            cash_balance=snapshot.total_cash,
            total_market_value=snapshot.total_market_value,
        )

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        return self.snapshots[account_id]


class FailingPortfolioProvider:
    """Provider test double that raises provider-neutral errors."""

    def list_accounts(self) -> tuple[str, ...]:
        return ("main",)

    def get_portfolio(self, account_id: str) -> Portfolio:
        raise PortfolioDataUnavailableError(f"portfolio unavailable: {account_id}")

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        raise PortfolioDataUnavailableError(f"portfolio unavailable: {account_id}")


def _snapshot(account_id: str = "main") -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id=account_id,
        as_of=AS_OF,
        holdings=(
            PortfolioHolding(
                symbol="AAA",
                name="Alpha Systems",
                quantity=10,
                average_cost=70,
                current_price=100,
                sector="Technology",
            ),
            PortfolioHolding(
                symbol="BBB",
                name="Beta Health",
                quantity=5,
                average_cost=80,
                current_price=100,
                sector="Healthcare",
            ),
            PortfolioHolding(
                symbol="CCC",
                name="Cashlike Components",
                quantity=5,
                average_cost=30,
                current_price=50,
                sector=None,
            ),
        ),
        cash_balances=(PortfolioCashBalance(amount=250),),
    )


def _provider(snapshot: PortfolioSnapshot | None = None) -> PortfolioContextProvider:
    portfolio_provider = StaticPortfolioProvider({"main": snapshot or _snapshot()})
    return PortfolioContextProvider(portfolio_provider, account_id="main")


def _rendered_context(provider: PortfolioContextProvider | None = None) -> str:
    context = ContextService(providers=(provider or _provider(),)).build_context(
        ContextRequest(question="Review portfolio state.", symbols=("AAA",))
    )
    return MeetingContextPromptRenderer().render(context)


def test_portfolio_context_provider_can_be_created() -> None:
    portfolio_provider = StaticPortfolioProvider({"main": _snapshot()})
    provider = PortfolioContextProvider(portfolio_provider, account_id="main")

    assert provider.provider_name == "portfolio"
    assert provider.supports(ContextRequest(question="Review.", symbols=())) is True


def test_generated_context_includes_portfolio_summary() -> None:
    rendered = _rendered_context()

    assert "### Portfolio Summary" in rendered
    assert "account_id=main" in rendered
    assert "total_equity=2000.0" in rendered
    assert "total_market_value=1750.0" in rendered
    assert "total_cash=250.0" in rendered
    assert "holding_count=3" in rendered
    assert "symbols=AAA, BBB, CCC" in rendered


def test_generated_context_includes_top_holdings() -> None:
    rendered = _rendered_context()

    assert "### Top Holdings" in rendered
    assert "AAA: name=Alpha Systems" in rendered
    assert "market_value=1000.0" in rendered
    assert "weight=0.5" in rendered


def test_generated_context_includes_sector_allocation() -> None:
    rendered = _rendered_context()

    assert "### Sector Allocation" in rendered
    assert "- Healthcare: value=500.0, percent=0.25" in rendered
    assert "- Technology: value=1000.0, percent=0.5" in rendered
    assert "- Unknown: value=250.0, percent=0.125" in rendered


def test_generated_context_includes_risk_summary() -> None:
    rendered = _rendered_context()

    assert "### Risk Summary" in rendered
    assert "largest_holding_symbol=AAA" in rendered
    assert "top_5_concentration=0.875" in rendered
    assert "cash_weight=0.125" in rendered
    assert "sector_count=3" in rendered


def test_empty_portfolio_renders_safely() -> None:
    provider = _provider(PortfolioSnapshot(account_id="main", as_of=AS_OF))

    rendered = _rendered_context(provider)

    assert "### Portfolio Summary" in rendered
    assert "total_equity=0" in rendered
    assert "holding_count=0" in rendered
    assert "symbols=None" in rendered
    assert "### Top Holdings\n- None" in rendered
    assert "### Sector Allocation\n- None" in rendered
    assert "largest_holding_symbol" not in rendered


def test_unsupported_request_uses_context_layer_error() -> None:
    provider = _provider()
    request = ContextRequest(
        question="Review without portfolio.",
        symbols=("AAA",),
        include_portfolio=False,
    )

    with pytest.raises(UnsupportedContextRequestError, match="portfolio"):
        provider.build_context(request)


def test_provider_errors_propagate_consistently() -> None:
    provider = PortfolioContextProvider(
        FailingPortfolioProvider(),
        account_id="main",
    )

    with pytest.raises(PortfolioDataUnavailableError, match="portfolio unavailable"):
        provider.build_context(ContextRequest(question="Review.", symbols=("AAA",)))


def test_no_recommendation_language_is_included() -> None:
    rendered = _rendered_context().lower()

    for forbidden_word in ("recommendation", "action", "buy", "sell", "hold"):
        assert re.search(rf"\b{forbidden_word}\b", rendered) is None


def test_portfolio_context_provider_implements_context_provider_contract() -> None:
    provider: object = _provider()

    assert isinstance(provider, PortfolioContextProvider)
    assert provider.build_context(ContextRequest(question="Review.", symbols=()))


def test_portfolio_context_provider_accepts_portfolio_provider_protocol() -> None:
    provider: PortfolioProvider = StaticPortfolioProvider({"main": _snapshot()})
    context_provider = PortfolioContextProvider(
        provider,
        account_id="main",
    )

    assert context_provider.build_context(
        ContextRequest(question="Review.", symbols=("AAA",))
    ).partial_context.portfolio is not None
