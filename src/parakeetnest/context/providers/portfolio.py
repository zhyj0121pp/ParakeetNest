"""Portfolio context provider backed by the PortfolioProvider abstraction."""

from __future__ import annotations

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    PortfolioAllocationContextItem,
    PortfolioPosition,
    PortfolioSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.portfolio.mock_provider import MockPortfolioProvider
from parakeetnest.portfolio.models import PortfolioHolding
from parakeetnest.portfolio.provider import PortfolioProvider


class PortfolioContextProvider:
    """Expose provider-neutral portfolio context to the Context Layer."""

    provider_name = "portfolio"

    def __init__(
        self,
        portfolio_provider: PortfolioProvider | None = None,
        account_id: str = "mock-main",
    ) -> None:
        self._portfolio_provider = portfolio_provider or MockPortfolioProvider()
        self._account_id = account_id

    def supports(self, request: ContextRequest) -> bool:
        return request.include_portfolio

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        snapshot = self._portfolio_provider.get_snapshot(self._account_id)
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
                    PortfolioAllocationContextItem(
                        category=holding.symbol,
                        value=holding.market_value,
                        percent=holding.weight_in_portfolio(snapshot.total_equity),
                    )
                    for holding in snapshot.holdings
                ),
                positions=positions,
                cash_balance=snapshot.total_cash,
                total_value=snapshot.total_equity,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={
                "source": "mock_portfolio_provider",
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
