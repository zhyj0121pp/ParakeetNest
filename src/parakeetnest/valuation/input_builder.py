"""Build provider-neutral valuation inputs from normalized context snapshots."""

from __future__ import annotations

from datetime import date

from parakeetnest.context.models import (
    ContextRequest,
    FinancialStatementItem,
    FinancialStatementSnapshot,
    MarketDataPoint,
    MarketSnapshot,
)
from parakeetnest.valuation.models import (
    ValuationConfidence,
    ValuationInput,
    ValuationMethod,
    ValuationMetric,
)


class ValuationInputBuilder:
    """Prepare valuation input values from existing normalized context."""

    _FINANCIAL_FIELDS = (
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "total_equity",
        "free_cash_flow",
    )

    def __init__(
        self,
        method: ValuationMethod = ValuationMethod.HISTORICAL_MULTIPLES,
    ) -> None:
        self._method = method

    def build(
        self,
        symbol: str,
        request: ContextRequest,
        market: MarketSnapshot | None = None,
        financials: FinancialStatementSnapshot | None = None,
    ) -> ValuationInput:
        """Return normalized valuation inputs for one requested symbol."""
        normalized_symbol = symbol.strip().upper()
        market_point = self._market_point_for(normalized_symbol, market)
        financial_item = self._financial_item_for(normalized_symbol, financials)

        metrics: dict[ValuationMetric, float | None] = {}
        assumptions: dict[str, float | str | None] = {}
        notes = ["Valuation inputs normalized from context snapshots."]

        if market_point is None:
            notes.append("No market snapshot data matched the requested symbol.")
        else:
            self._add_metric(
                metrics,
                ValuationMetric.MARKET_CAP,
                self._number(market_point.market_cap),
            )
            self._add_metric(
                metrics,
                ValuationMetric.ENTERPRISE_VALUE,
                self._number(getattr(market_point, "enterprise_value", None)),
            )

        if financial_item is None:
            notes.append(
                "No financial statement snapshot data matched the requested symbol."
            )
        else:
            for field_name in self._FINANCIAL_FIELDS:
                self._add_assumption(
                    assumptions,
                    field_name,
                    self._number(getattr(financial_item, field_name)),
                )
            self._add_assumption(
                assumptions,
                "ebitda",
                self._number(getattr(financial_item, "ebitda", None)),
            )

        return ValuationInput(
            symbol=normalized_symbol,
            method=self._method,
            as_of_date=self._as_of_date(request),
            fiscal_period=self._fiscal_period_for(financial_item),
            metrics=metrics,
            assumptions=assumptions,
            data_sources=self._data_sources(market, market_point, financials, financial_item),
            calculation_notes=notes,
            confidence=self._confidence(market_point, financial_item),
        )

    def __call__(
        self,
        symbol: str,
        request: ContextRequest,
        market: MarketSnapshot | None = None,
        financials: FinancialStatementSnapshot | None = None,
    ) -> ValuationInput:
        """Allow the builder to be injected anywhere a callable is expected."""
        return self.build(symbol, request, market, financials)

    @staticmethod
    def _market_point_for(
        symbol: str,
        market: MarketSnapshot | None,
    ) -> MarketDataPoint | None:
        if market is None:
            return None
        return next(
            (
                point
                for point in market.points
                if point.symbol.strip().upper() == symbol
            ),
            None,
        )

    @staticmethod
    def _financial_item_for(
        symbol: str,
        financials: FinancialStatementSnapshot | None,
    ) -> FinancialStatementItem | None:
        if financials is None:
            return None
        return next(
            (
                item
                for item in financials.items
                if item.symbol.strip().upper() == symbol
            ),
            None,
        )

    @staticmethod
    def _as_of_date(request: ContextRequest) -> date:
        if request.as_of is not None:
            return request.as_of.date()
        return date.today()

    @staticmethod
    def _fiscal_period_for(item: FinancialStatementItem | None) -> str | None:
        if item is None:
            return None
        if item.period_type == "quarterly" and item.fiscal_year and item.fiscal_quarter:
            return f"FY{item.fiscal_year}Q{item.fiscal_quarter}"
        if item.fiscal_year:
            return f"FY{item.fiscal_year}"
        if item.period_type:
            return item.period_type.upper()
        return None

    @staticmethod
    def _data_sources(
        market: MarketSnapshot | None,
        market_point: MarketDataPoint | None,
        financials: FinancialStatementSnapshot | None,
        financial_item: FinancialStatementItem | None,
    ) -> list[str]:
        sources: list[str] = []
        for source in (
            market.source if market is not None else None,
            market_point.source if market_point is not None else None,
            financials.source if financials is not None else None,
            financial_item.source if financial_item is not None else None,
        ):
            if source and source not in sources:
                sources.append(source)
        return sources

    @staticmethod
    def _confidence(
        market_point: MarketDataPoint | None,
        financial_item: FinancialStatementItem | None,
    ) -> ValuationConfidence:
        if market_point is not None and financial_item is not None:
            return ValuationConfidence.HIGH
        if market_point is not None or financial_item is not None:
            return ValuationConfidence.MEDIUM
        return ValuationConfidence.LOW

    @staticmethod
    def _add_metric(
        metrics: dict[ValuationMetric, float | None],
        metric: ValuationMetric,
        value: float | None,
    ) -> None:
        if value is not None:
            metrics[metric] = value

    @staticmethod
    def _add_assumption(
        assumptions: dict[str, float | str | None],
        name: str,
        value: float | None,
    ) -> None:
        if value is not None:
            assumptions[name] = value

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        return None


__all__ = ["ValuationInputBuilder"]
