"""Portfolio context provider backed by the PortfolioService boundary."""

from __future__ import annotations

from decimal import Decimal

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    PortfolioAllocationContextItem,
    PortfolioPosition,
    PortfolioRiskSummaryContext,
    PortfolioSnapshot as ContextPortfolioSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.portfolio.models import (
    PortfolioAllocation,
    PortfolioHolding,
    PortfolioRiskSummary,
    PortfolioSnapshot,
)
from parakeetnest.portfolio.service import PortfolioService


class PortfolioContextProvider:
    """Expose read-only portfolio intelligence through the Context Layer."""

    provider_name = "portfolio"

    def __init__(
        self,
        portfolio_service: PortfolioService,
        account_id: str,
    ) -> None:
        self._portfolio_service = portfolio_service
        self._account_id = account_id

    def supports(self, request: ContextRequest) -> bool:
        return request.include_portfolio

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        snapshot = self._portfolio_service.get_snapshot(self._account_id)
        top_holdings = self._portfolio_service.get_top_holdings(self._account_id)
        allocation_by_symbol = self._portfolio_service.get_allocation_by_symbol(
            self._account_id
        )
        allocation_by_sector = self._portfolio_service.get_allocation_by_sector(
            self._account_id
        )
        risk_summary = self._portfolio_service.get_risk_summary(self._account_id)

        fetched_at = request.as_of or snapshot.as_of
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            portfolio=ContextPortfolioSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                account_id=snapshot.account_id,
                total_equity=snapshot.total_equity,
                total_market_value=snapshot.total_market_value,
                total_cash=snapshot.total_cash,
                holding_count=snapshot.holding_count(),
                symbols=snapshot.symbols(),
                top_holdings=tuple(
                    self._position_for(holding, snapshot.total_equity)
                    for holding in top_holdings
                ),
                allocation_by_symbol=tuple(
                    self._allocation_for(allocation)
                    for allocation in allocation_by_symbol
                ),
                allocation_by_sector=tuple(
                    self._allocation_for(allocation)
                    for allocation in allocation_by_sector
                ),
                risk_summary=self._risk_summary_for(risk_summary),
                positions=tuple(
                    self._position_for(holding, snapshot.total_equity)
                    for holding in snapshot.holdings
                ),
                cash_balance=snapshot.total_cash,
                total_value=snapshot.total_equity,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "portfolio_service", "account_id": snapshot.account_id},
        )

    @staticmethod
    def _position_for(
        holding: PortfolioHolding,
        total_equity: float | None,
    ) -> PortfolioPosition:
        cost_basis = holding.quantity * holding.average_cost
        return PortfolioPosition(
            symbol=holding.symbol,
            name=holding.name,
            quantity=holding.quantity,
            market_value=holding.market_value,
            cost_basis=cost_basis,
            unrealized_pl=holding.unrealized_gain_loss,
            weight=holding.weight_in_portfolio(total_equity or 0.0),
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


def _float(value: Decimal | float | int) -> float:
    """Return a renderer-friendly float for numeric context fields."""
    return float(value)


__all__ = ["PortfolioContextProvider"]
