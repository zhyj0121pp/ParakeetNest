"""Normalized domain snapshots used between services and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class HoldingSnapshot:
    """Normalized portfolio holding data for one symbol."""

    symbol: str
    quantity: float
    cost_basis: float | None = None
    market_value: float | None = None
    unrealized_pl: float | None = None


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Normalized portfolio snapshot collected from a portfolio source."""

    source: str
    fetched_at: datetime | None
    holdings: tuple[HoldingSnapshot, ...] = field(default_factory=tuple)
    cash_balance: float | None = None


@dataclass(frozen=True)
class MarketSnapshot:
    """Normalized market data snapshot for one symbol."""

    source: str
    fetched_at: datetime | None
    symbol: str
    price: float | None = None
    daily_change: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None


@dataclass(frozen=True)
class FinancialSnapshot:
    """Normalized financial data snapshot for one symbol and period."""

    source: str
    fetched_at: datetime | None
    symbol: str
    period: str | None = None
    revenue: float | None = None
    eps: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    free_cash_flow: float | None = None


@dataclass(frozen=True)
class NewsSnapshot:
    """Normalized news item snapshot."""

    source: str
    fetched_at: datetime | None
    title: str
    symbol: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class MacroSnapshot:
    """Normalized macro indicator snapshot."""

    source: str
    fetched_at: datetime | None
    indicator: str
    value: float | None = None
    unit: str | None = None
    observed_on: date | None = None


@dataclass(frozen=True)
class CalendarSnapshot:
    """Normalized investment calendar event snapshot."""

    source: str
    fetched_at: datetime | None
    event_type: str
    title: str
    event_at: datetime | None = None
    symbol: str | None = None
