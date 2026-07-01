"""Tests for the portfolio intelligence service."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from parakeetnest.portfolio import (
    PortfolioCashBalance,
    PortfolioDataUnavailableError,
    PortfolioHolding,
    PortfolioProvider,
    PortfolioService,
    PortfolioSnapshot,
)


AS_OF = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


class SpyPortfolioProvider:
    """Small provider test double that records delegation calls."""

    def __init__(self, snapshots: dict[str, PortfolioSnapshot]) -> None:
        self.snapshots = snapshots
        self.list_accounts_calls = 0
        self.get_snapshot_calls: list[str] = []

    def list_accounts(self) -> tuple[str, ...]:
        self.list_accounts_calls += 1
        return tuple(self.snapshots)

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        self.get_snapshot_calls.append(account_id)
        return self.snapshots[account_id]


class FailingPortfolioProvider:
    """Provider test double that raises provider errors."""

    def list_accounts(self) -> tuple[str, ...]:
        return ("main",)

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        raise PortfolioDataUnavailableError(f"unavailable: {account_id}")


def _snapshot(account_id: str = "main") -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id=account_id,
        as_of=AS_OF,
        holdings=(
            PortfolioHolding(
                symbol="AAA",
                name="Alpha",
                quantity=10,
                average_cost=70,
                current_price=100,
                sector="Technology",
            ),
            PortfolioHolding(
                symbol="BBB",
                name="Beta",
                quantity=5,
                average_cost=80,
                current_price=100,
                sector="Healthcare",
            ),
            PortfolioHolding(
                symbol="CCC",
                name="Gamma",
                quantity=5,
                average_cost=30,
                current_price=50,
                sector=None,
            ),
        ),
        cash_balances=(PortfolioCashBalance(amount=250),),
    )


def test_list_accounts_delegates_to_provider() -> None:
    """Account listing should come directly from the provider."""
    provider = SpyPortfolioProvider({"main": _snapshot()})
    service = PortfolioService(provider)

    assert service.list_accounts() == ("main",)
    assert provider.list_accounts_calls == 1


def test_get_snapshot_delegates_to_provider() -> None:
    """Snapshot loading should come directly from the provider."""
    snapshot = _snapshot()
    provider = SpyPortfolioProvider({"main": snapshot})
    service = PortfolioService(provider)

    assert service.get_snapshot("main") is snapshot
    assert provider.get_snapshot_calls == ["main"]


def test_get_symbols() -> None:
    """Symbols should be returned in snapshot holding order."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    assert service.get_symbols("main") == ("AAA", "BBB", "CCC")


def test_get_total_equity() -> None:
    """Total equity should be exposed as Decimal money."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    assert service.get_total_equity("main") == Decimal("2000.0")


def test_get_allocation_by_symbol() -> None:
    """Symbol allocations should use market value over total equity."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    allocations = service.get_allocation_by_symbol("main")

    assert [(item.label, item.value, item.weight) for item in allocations] == [
        ("AAA", Decimal("1000.0"), Decimal("0.5")),
        ("BBB", Decimal("500.0"), Decimal("0.25")),
        ("CCC", Decimal("250.0"), Decimal("0.125")),
    ]


def test_get_allocation_by_sector() -> None:
    """Sector allocations should group holdings by sector."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    allocations = service.get_allocation_by_sector("main")

    assert [(item.label, item.value, item.weight) for item in allocations] == [
        ("Healthcare", Decimal("500.0"), Decimal("0.25")),
        ("Technology", Decimal("1000.0"), Decimal("0.5")),
        ("Unknown", Decimal("250.0"), Decimal("0.125")),
    ]


def test_missing_sector_grouped_as_unknown() -> None:
    """Holdings without sector metadata should be grouped as Unknown."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    unknown = {
        allocation.label: allocation
        for allocation in service.get_allocation_by_sector("main")
    }["Unknown"]

    assert unknown.value == Decimal("250.0")
    assert unknown.weight == Decimal("0.125")


def test_get_top_holdings_sorted_by_market_value() -> None:
    """Top holdings should sort largest market value first."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    assert [holding.symbol for holding in service.get_top_holdings("main")] == [
        "AAA",
        "BBB",
        "CCC",
    ]


def test_get_top_holdings_limit() -> None:
    """The top-holdings limit should cap returned holdings."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    assert [holding.symbol for holding in service.get_top_holdings("main", limit=2)] == [
        "AAA",
        "BBB",
    ]


def test_invalid_top_holdings_limit() -> None:
    """Non-positive top-holdings limits should be rejected."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    with pytest.raises(ValueError, match="limit must be positive"):
        service.get_top_holdings("main", limit=0)


def test_get_risk_summary_for_non_empty_portfolio() -> None:
    """Risk summary should expose simple deterministic concentration metrics."""
    service = PortfolioService(SpyPortfolioProvider({"main": _snapshot()}))

    summary = service.get_risk_summary("main")

    assert summary.holding_count == 3
    assert summary.largest_holding_symbol == "AAA"
    assert summary.largest_holding_weight == Decimal("0.5")
    assert summary.top_5_concentration == Decimal("0.875")
    assert summary.cash_weight == Decimal("0.125")
    assert summary.sector_count == 3
    assert summary.largest_position_symbol == "AAA"


def test_get_risk_summary_for_empty_portfolio() -> None:
    """Empty snapshots should return a zero risk summary."""
    empty = PortfolioSnapshot(account_id="empty", as_of=AS_OF)
    service = PortfolioService(SpyPortfolioProvider({"empty": empty}))

    summary = service.get_risk_summary("empty")

    assert summary.holding_count == 0
    assert summary.largest_holding_symbol is None
    assert summary.largest_holding_weight == Decimal("0")
    assert summary.top_5_concentration == Decimal("0")
    assert summary.cash_weight == Decimal("0")
    assert summary.sector_count == 0


def test_provider_errors_propagate() -> None:
    """Provider errors should not be swallowed by the service."""
    provider: PortfolioProvider = FailingPortfolioProvider()
    service = PortfolioService(provider)

    with pytest.raises(PortfolioDataUnavailableError, match="unavailable: main"):
        service.get_snapshot("main")
