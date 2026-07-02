"""Provider-neutral Portfolio Intelligence domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


@dataclass(frozen=True)
class Holding:
    """Minimal provider-neutral portfolio holding."""

    ticker: str
    quantity: float
    market_value: float
    portfolio_weight: float
    average_cost: float | None = None
    unrealized_gain_loss: float | None = None

    def __post_init__(self) -> None:
        """Normalize broker-neutral holding values."""
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        object.__setattr__(self, "quantity", float(self.quantity))
        object.__setattr__(self, "market_value", float(self.market_value))
        object.__setattr__(self, "portfolio_weight", float(self.portfolio_weight))
        if self.average_cost is not None:
            object.__setattr__(self, "average_cost", float(self.average_cost))
        if self.unrealized_gain_loss is not None:
            object.__setattr__(
                self,
                "unrealized_gain_loss",
                float(self.unrealized_gain_loss),
            )


@dataclass(frozen=True)
class Portfolio:
    """Minimal provider-neutral portfolio snapshot."""

    cash_balance: float
    total_market_value: float
    holdings: tuple[Holding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize portfolio values and immutable holdings collection."""
        object.__setattr__(self, "cash_balance", float(self.cash_balance))
        object.__setattr__(self, "total_market_value", float(self.total_market_value))
        object.__setattr__(self, "holdings", tuple(self.holdings))

    def tickers(self) -> tuple[str, ...]:
        """Return normalized holding tickers in portfolio order."""
        return tuple(holding.ticker for holding in self.holdings)


class PortfolioAssetType(str, Enum):
    """Provider-neutral asset classes supported by portfolio v1."""

    EQUITY = "equity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    OPTION = "option"
    BOND = "bond"
    CASH = "cash"
    CRYPTO = "crypto"
    OTHER = "other"


class PortfolioPositionType(str, Enum):
    """Provider-neutral position direction."""

    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class PortfolioHolding:
    """Point-in-time view of a portfolio holding."""

    symbol: str
    name: str
    quantity: float
    average_cost: float
    current_price: float
    asset_type: PortfolioAssetType = PortfolioAssetType.EQUITY
    position_type: PortfolioPositionType = PortfolioPositionType.LONG
    market_value: float | None = None
    unrealized_gain_loss: float | None = None
    unrealized_gain_loss_percent: float | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Normalize stable portfolio identity and calculated values."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "quantity", float(self.quantity))
        object.__setattr__(self, "average_cost", float(self.average_cost))
        object.__setattr__(self, "current_price", float(self.current_price))
        if not isinstance(self.asset_type, PortfolioAssetType):
            object.__setattr__(self, "asset_type", PortfolioAssetType(self.asset_type))
        if not isinstance(self.position_type, PortfolioPositionType):
            object.__setattr__(
                self,
                "position_type",
                PortfolioPositionType(self.position_type),
            )
        object.__setattr__(
            self,
            "market_value",
            float(self.market_value)
            if self.market_value is not None
            else self.quantity * self.current_price,
        )
        calculated_gain_loss = self.market_value - (self.quantity * self.average_cost)
        object.__setattr__(
            self,
            "unrealized_gain_loss",
            float(self.unrealized_gain_loss)
            if self.unrealized_gain_loss is not None
            else calculated_gain_loss,
        )
        cost_basis = self.quantity * self.average_cost
        object.__setattr__(
            self,
            "unrealized_gain_loss_percent",
            float(self.unrealized_gain_loss_percent)
            if self.unrealized_gain_loss_percent is not None
            else _safe_percent(self.unrealized_gain_loss, cost_basis),
        )
        if self.sector is not None:
            object.__setattr__(self, "sector", self.sector.strip() or None)
        if self.industry is not None:
            object.__setattr__(self, "industry", self.industry.strip() or None)
        object.__setattr__(self, "currency", self.currency.strip().upper() or "USD")

    def weight_in_portfolio(self, total_value: float) -> float:
        """Return this holding's market value as a fraction of total value."""
        if total_value == 0:
            return 0.0
        return self.market_value / float(total_value)


@dataclass(frozen=True)
class PortfolioCashBalance:
    """Cash balance for one currency in a portfolio account."""

    amount: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Normalize amount and currency."""
        object.__setattr__(self, "amount", float(self.amount))
        object.__setattr__(self, "currency", self.currency.strip().upper() or "USD")


@dataclass(frozen=True)
class PortfolioAllocation:
    """Portfolio allocation percentage for an asset, sector, or other bucket."""

    category: str
    value: Decimal
    percent: Decimal

    def __post_init__(self) -> None:
        """Normalize allocation fields."""
        object.__setattr__(self, "category", self.category.strip())
        object.__setattr__(self, "value", _decimal(self.value))
        object.__setattr__(self, "percent", _decimal(self.percent))

    @property
    def label(self) -> str:
        """Return the allocation label."""
        return self.category

    @property
    def weight(self) -> Decimal:
        """Return the allocation weight as a fraction of total equity."""
        return self.percent


@dataclass(frozen=True)
class PortfolioExposure:
    """Compact exposure summary for a portfolio dimension."""

    name: str
    market_value: float
    percent: float

    def __post_init__(self) -> None:
        """Normalize exposure fields."""
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "market_value", float(self.market_value))
        object.__setattr__(self, "percent", float(self.percent))


@dataclass(frozen=True)
class PortfolioRiskSummary:
    """Provider-neutral risk summary for portfolio-level context."""

    concentration_score: float = 0.0
    largest_position_symbol: str | None = None
    largest_position_weight: float = 0.0
    cash_weight: Decimal = Decimal("0")
    notes: tuple[str, ...] = field(default_factory=tuple)
    holding_count: int = 0
    largest_holding_symbol: str | None = None
    largest_holding_weight: Decimal = Decimal("0")
    top_5_concentration: Decimal = Decimal("0")
    sector_count: int = 0

    def __post_init__(self) -> None:
        """Normalize compact risk summary fields."""
        object.__setattr__(self, "concentration_score", float(self.concentration_score))
        largest_symbol = self.largest_holding_symbol or self.largest_position_symbol
        if self.largest_position_symbol is not None:
            object.__setattr__(
                self,
                "largest_position_symbol",
                self.largest_position_symbol.strip().upper() or None,
            )
        if largest_symbol is not None:
            object.__setattr__(
                self,
                "largest_position_symbol",
                largest_symbol.strip().upper() or None,
            )
            object.__setattr__(
                self,
                "largest_holding_symbol",
                largest_symbol.strip().upper() or None,
            )
        largest_weight = (
            self.largest_holding_weight
            if self.largest_holding_weight != Decimal("0")
            else self.largest_position_weight
        )
        object.__setattr__(
            self,
            "largest_position_weight",
            float(largest_weight),
        )
        object.__setattr__(self, "largest_holding_weight", _decimal(largest_weight))
        object.__setattr__(self, "cash_weight", _decimal(self.cash_weight))
        object.__setattr__(
            self,
            "top_5_concentration",
            _decimal(self.top_5_concentration),
        )
        object.__setattr__(self, "holding_count", int(self.holding_count))
        object.__setattr__(self, "sector_count", int(self.sector_count))
        object.__setattr__(
            self,
            "notes",
            tuple(note.strip() for note in self.notes if note.strip()),
        )


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Point-in-time provider-neutral portfolio account snapshot."""

    account_id: str
    as_of: datetime
    holdings: tuple[PortfolioHolding, ...] = field(default_factory=tuple)
    cash_balances: tuple[PortfolioCashBalance, ...] = field(default_factory=tuple)
    total_market_value: float | None = None
    total_cash: float | None = None
    total_equity: float | None = None
    total_unrealized_gain_loss: float | None = None
    total_unrealized_gain_loss_percent: float | None = None

    def __post_init__(self) -> None:
        """Normalize account identity, collections, and aggregate values."""
        object.__setattr__(self, "account_id", self.account_id.strip())
        object.__setattr__(self, "holdings", tuple(self.holdings))
        object.__setattr__(self, "cash_balances", tuple(self.cash_balances))

        calculated_market_value = sum(holding.market_value for holding in self.holdings)
        calculated_cash = sum(balance.amount for balance in self.cash_balances)
        calculated_unrealized = sum(
            holding.unrealized_gain_loss for holding in self.holdings
        )
        calculated_equity = calculated_market_value + calculated_cash
        calculated_cost_basis = sum(
            holding.quantity * holding.average_cost for holding in self.holdings
        )

        object.__setattr__(
            self,
            "total_market_value",
            float(self.total_market_value)
            if self.total_market_value is not None
            else calculated_market_value,
        )
        object.__setattr__(
            self,
            "total_cash",
            float(self.total_cash) if self.total_cash is not None else calculated_cash,
        )
        object.__setattr__(
            self,
            "total_equity",
            float(self.total_equity)
            if self.total_equity is not None
            else calculated_equity,
        )
        object.__setattr__(
            self,
            "total_unrealized_gain_loss",
            float(self.total_unrealized_gain_loss)
            if self.total_unrealized_gain_loss is not None
            else calculated_unrealized,
        )
        object.__setattr__(
            self,
            "total_unrealized_gain_loss_percent",
            float(self.total_unrealized_gain_loss_percent)
            if self.total_unrealized_gain_loss_percent is not None
            else _safe_percent(self.total_unrealized_gain_loss, calculated_cost_basis),
        )

    def symbols(self) -> tuple[str, ...]:
        """Return normalized holding symbols in snapshot order."""
        return tuple(holding.symbol for holding in self.holdings)

    def holding_count(self) -> int:
        """Return the number of holdings in the snapshot."""
        return len(self.holdings)

    def is_empty(self) -> bool:
        """Return whether the snapshot has no holdings and no cash."""
        return not self.holdings and self.total_cash == 0


def _safe_percent(numerator: float, denominator: float) -> float:
    """Return a fraction with a stable zero value for empty denominators."""
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _decimal(value: Decimal | float | int | str) -> Decimal:
    """Return a Decimal while preserving explicit float inputs."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal.from_float(value)
    return Decimal(str(value))


__all__ = [
    "Holding",
    "Portfolio",
    "PortfolioAllocation",
    "PortfolioAssetType",
    "PortfolioCashBalance",
    "PortfolioExposure",
    "PortfolioHolding",
    "PortfolioPositionType",
    "PortfolioRiskSummary",
    "PortfolioSnapshot",
]
