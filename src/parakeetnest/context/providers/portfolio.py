"""Portfolio context provider backed by the PortfolioProvider abstraction."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    PortfolioAllocationContextItem,
    PortfolioPosition,
    PortfolioRiskSummaryContext,
    PortfolioSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.portfolio.models import (
    PortfolioAllocation,
    PortfolioHolding,
    PortfolioRiskSummary,
    PortfolioSnapshot as ProviderPortfolioSnapshot,
)
from parakeetnest.portfolio.provider import PortfolioProvider


class PortfolioContextProvider:
    """Expose provider-neutral portfolio context to the Context Layer."""

    provider_name = "portfolio"

    def __init__(
        self,
        portfolio_provider: PortfolioProvider,
        account_id: str = "mock-main",
    ) -> None:
        self._portfolio_provider = portfolio_provider
        self._account_id = account_id

    def supports(self, request: ContextRequest) -> bool:
        return request.include_portfolio

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        snapshot = self._portfolio_provider.get_snapshot(self._account_id)
        top_holdings = _top_holdings(snapshot)
        allocation_by_symbol = _allocation_by_symbol(snapshot)
        allocation_by_sector = _allocation_by_sector(snapshot)
        risk_summary = _risk_summary(snapshot)
        fetched_at = request.as_of or snapshot.as_of
        positions = tuple(
            self._position_for(holding, snapshot.total_equity)
            for holding in snapshot.holdings
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            portfolio=PortfolioSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                account_id=snapshot.account_id,
                total_equity=snapshot.total_equity,
                total_market_value=snapshot.total_market_value,
                total_cash=snapshot.total_cash,
                holding_count=snapshot.holding_count(),
                symbols=snapshot.symbols(),
                allocation_by_symbol=tuple(
                    self._allocation_for(allocation)
                    for allocation in allocation_by_symbol
                ),
                allocation_by_sector=tuple(
                    self._allocation_for(allocation)
                    for allocation in allocation_by_sector
                ),
                top_holdings=tuple(
                    self._position_for(holding, snapshot.total_equity)
                    for holding in top_holdings
                ),
                risk_summary=self._risk_summary_for(risk_summary),
                positions=positions,
                cash_balance=snapshot.total_cash,
                total_value=snapshot.total_equity,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={
                "source": "portfolio_provider",
                "account_id": snapshot.account_id,
            },
        )

    @staticmethod
    def _position_for(
        holding: PortfolioHolding,
        total_value: float | None,
    ) -> PortfolioPosition:
        return PortfolioPosition(
            symbol=holding.symbol,
            name=holding.name,
            quantity=holding.quantity,
            market_value=holding.market_value,
            cost_basis=holding.quantity * holding.average_cost,
            unrealized_pl=holding.unrealized_gain_loss,
            weight=holding.weight_in_portfolio(total_value or 0.0),
            sector=holding.sector,
        )

    @staticmethod
    def _allocation_for(
        allocation: PortfolioAllocation,
    ) -> PortfolioAllocationContextItem:
        return PortfolioAllocationContextItem(
            category=allocation.category,
            value=float(allocation.value),
            percent=float(allocation.percent),
        )

    @staticmethod
    def _risk_summary_for(
        risk_summary: PortfolioRiskSummary,
    ) -> PortfolioRiskSummaryContext:
        return PortfolioRiskSummaryContext(
            concentration_score=risk_summary.concentration_score,
            largest_holding_symbol=risk_summary.largest_holding_symbol,
            largest_holding_weight=_float(risk_summary.largest_holding_weight),
            top_5_concentration=_float(risk_summary.top_5_concentration),
            cash_weight=_float(risk_summary.cash_weight),
            holding_count=risk_summary.holding_count,
            sector_count=risk_summary.sector_count,
            notes=risk_summary.notes,
        )


def _allocation_by_symbol(
    snapshot: ProviderPortfolioSnapshot,
) -> tuple[PortfolioAllocation, ...]:
    """Return holding allocations by symbol from one provider snapshot."""
    total_equity = _decimal(snapshot.total_equity)
    if total_equity == 0:
        return ()

    return tuple(
        PortfolioAllocation(
            category=holding.symbol,
            value=_decimal(holding.market_value),
            percent=_weight(holding.market_value, total_equity),
        )
        for holding in snapshot.holdings
    )


def _allocation_by_sector(
    snapshot: ProviderPortfolioSnapshot,
) -> tuple[PortfolioAllocation, ...]:
    """Return holding allocations grouped by sector from one snapshot."""
    total_equity = _decimal(snapshot.total_equity)
    if total_equity == 0:
        return ()

    sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for holding in snapshot.holdings:
        sector_values[holding.sector or "Unknown"] += _decimal(holding.market_value)

    return tuple(
        PortfolioAllocation(category=sector, value=value, percent=value / total_equity)
        for sector, value in sorted(sector_values.items())
    )


def _top_holdings(
    snapshot: ProviderPortfolioSnapshot,
    limit: int = 5,
) -> tuple[PortfolioHolding, ...]:
    """Return largest holdings by market value from one snapshot."""
    return tuple(
        sorted(
            snapshot.holdings,
            key=lambda holding: (-_decimal(holding.market_value), holding.symbol),
        )[:limit]
    )


def _risk_summary(snapshot: ProviderPortfolioSnapshot) -> PortfolioRiskSummary:
    """Return simple provider-neutral portfolio risk context."""
    if snapshot.is_empty():
        return PortfolioRiskSummary()

    total_equity = _decimal(snapshot.total_equity)
    if total_equity == 0:
        return PortfolioRiskSummary(holding_count=snapshot.holding_count())

    top_holdings = _top_holdings(snapshot)
    largest_holding = top_holdings[0] if top_holdings else None
    largest_holding_weight = (
        _weight(largest_holding.market_value, total_equity)
        if largest_holding is not None
        else Decimal("0")
    )
    top_5_concentration = sum(
        (_decimal(holding.market_value) for holding in top_holdings),
        Decimal("0"),
    ) / total_equity
    sectors = {holding.sector or "Unknown" for holding in snapshot.holdings}

    return PortfolioRiskSummary(
        concentration_score=float(top_5_concentration),
        largest_position_symbol=largest_holding.symbol if largest_holding else None,
        largest_position_weight=float(largest_holding_weight),
        holding_count=snapshot.holding_count(),
        largest_holding_symbol=largest_holding.symbol if largest_holding else None,
        largest_holding_weight=largest_holding_weight,
        top_5_concentration=top_5_concentration,
        cash_weight=_weight(snapshot.total_cash, total_equity),
        sector_count=len(sectors),
    )


def _decimal(value: Decimal | float | int | str | None) -> Decimal:
    """Return a Decimal using string conversion for provider float values."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _float(value: Decimal | float | int) -> float:
    """Return a renderer-friendly float for numeric context fields."""
    return float(value)


def _weight(value: Decimal | float | int | str | None, total: Decimal) -> Decimal:
    """Return a stable Decimal fraction for a value over total."""
    if total == 0:
        return Decimal("0")
    return _decimal(value) / total
