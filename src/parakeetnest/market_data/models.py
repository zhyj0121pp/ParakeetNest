"""Provider-agnostic Market Data Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class Symbol:
    """Normalized market symbol with optional venue metadata."""

    ticker: str
    exchange: str | None = None
    market: str | None = None

    def __post_init__(self) -> None:
        """Normalize symbol components for stable comparisons."""
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        if self.exchange is not None:
            object.__setattr__(self, "exchange", self.exchange.strip().upper())
        if self.market is not None:
            object.__setattr__(self, "market", self.market.strip().upper())


class AssetType(str, Enum):
    """Supported provider-independent asset classes."""

    STOCK = "stock"
    ETF = "etf"
    INDEX = "index"
    CRYPTO = "crypto"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MarketDataSnapshot:
    """Current point-in-time market data for one symbol."""

    symbol: Symbol
    asset_type: AssetType
    price: float
    currency: str
    timestamp: datetime
    previous_close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class CompanyInfo:
    """Basic provider-neutral company profile information."""

    symbol: Symbol
    name: str
    asset_type: AssetType = AssetType.UNKNOWN
    exchange: str | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    website: str | None = None
    market_cap: float | None = None
    full_time_employees: int | None = None
    summary: str | None = None


@dataclass(frozen=True)
class PriceBar:
    """OHLCV market data for one time interval."""

    symbol: Symbol
    start_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(frozen=True)
class MarketDataRange:
    """Requested historical market data range and granularity."""

    period: str | None = None
    interval: str | None = None
    start: datetime | None = None
    end: datetime | None = None
