"""Pure domain models for the Context Layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class ContextRequest:
    """Request to assemble research context before committee reasoning."""

    question: str
    symbols: tuple[str, ...]
    as_of: datetime | None = None
    include_portfolio: bool = True
    include_macro: bool = True
    include_knowledge_base: bool = True


@dataclass(frozen=True)
class MarketDataPoint:
    """One market observation for a symbol."""

    symbol: str
    source: str
    observed_at: datetime | None = None
    price: float | None = None
    daily_change: float | None = None
    daily_change_percent: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None


@dataclass(frozen=True)
class MarketSnapshot:
    """Market data available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    points: tuple[MarketDataPoint, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NewsItem:
    """One news item relevant to the requested context."""

    title: str
    source: str
    symbol: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class NewsContext:
    """News available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    items: tuple[NewsItem, ...] = field(default_factory=tuple)


NewsSnapshot = NewsContext


@dataclass(frozen=True)
class FilingItem:
    """One regulatory filing relevant to the requested context."""

    symbol: str
    filing_type: str
    source: str
    filed_at: datetime | None = None
    accession_number: str | None = None
    url: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class FilingSnapshot:
    """Regulatory filings available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    items: tuple[FilingItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FinancialStatementItem:
    """Financial statement context for one symbol and fiscal period."""

    symbol: str
    period_type: str
    source: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    cash: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None
    currency: str | None = None


@dataclass(frozen=True)
class FinancialStatementSnapshot:
    """Financial statements available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    items: tuple[FinancialStatementItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValuationContextItem:
    """Valuation context for one symbol and fiscal period."""

    symbol: str
    as_of_date: date
    fiscal_period: str | None = None
    metrics: dict[str, float | None] = field(default_factory=dict)
    calculation_notes: tuple[str, ...] = field(default_factory=tuple)
    confidence: str = "unknown"
    data_sources: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValuationContextSnapshot:
    """Valuation snapshots available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    items: tuple[ValuationContextItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PortfolioPosition:
    """One portfolio position relevant to the requested context."""

    symbol: str
    quantity: float
    name: str | None = None
    market_value: float | None = None
    cost_basis: float | None = None
    unrealized_pl: float | None = None
    weight: float | None = None
    sector: str | None = None


@dataclass(frozen=True)
class PortfolioAllocationContextItem:
    """One portfolio allocation bucket for committee context."""

    category: str
    value: float
    percent: float


@dataclass(frozen=True)
class PortfolioRiskSummaryContext:
    """Portfolio risk summary rendered before committee reasoning."""

    concentration_score: float = 0.0
    largest_holding_symbol: str | None = None
    largest_holding_weight: float = 0.0
    top_5_concentration: float = 0.0
    cash_weight: float = 0.0
    holding_count: int = 0
    sector_count: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Portfolio state available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    account_id: str | None = None
    total_equity: float | None = None
    total_market_value: float | None = None
    total_cash: float | None = None
    holding_count: int | None = None
    symbols: tuple[str, ...] = field(default_factory=tuple)
    top_holdings: tuple[PortfolioPosition, ...] = field(default_factory=tuple)
    allocation_by_symbol: tuple[PortfolioAllocationContextItem, ...] = (
        field(default_factory=tuple)
    )
    allocation_by_sector: tuple[PortfolioAllocationContextItem, ...] = (
        field(default_factory=tuple)
    )
    risk_summary: PortfolioRiskSummaryContext | None = None
    positions: tuple[PortfolioPosition, ...] = field(default_factory=tuple)
    cash_balance: float | None = None
    total_value: float | None = None


@dataclass(frozen=True)
class MacroSnapshot:
    """Macro context available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    indicators: tuple[str, ...] = field(default_factory=tuple)
    observed_on: date | None = None
    summary: str | None = None


@dataclass(frozen=True)
class EconomicRegimeContextSnapshot:
    """Economic regime context available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    regime: str = "unknown"
    confidence: str = "unknown"
    observed_on: date | None = None
    indicators: tuple[str, ...] = field(default_factory=tuple)
    summary: str | None = None
    regime_source: str | None = None


@dataclass(frozen=True)
class SectorRotationContextSnapshot:
    """Sector rotation context available to a context assembly."""

    source: str
    as_of_date: date
    fetched_at: datetime | None = None
    summary: str | None = None
    leaders: tuple[str, ...] = field(default_factory=tuple)
    improving: tuple[str, ...] = field(default_factory=tuple)
    weakening: tuple[str, ...] = field(default_factory=tuple)
    laggards: tuple[str, ...] = field(default_factory=tuple)
    unknown: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MarketBreadthContextSnapshot:
    """Market breadth context available to a context assembly."""

    source: str
    as_of_date: date
    universe: str
    fetched_at: datetime | None = None
    breadth_regime: str = "unknown"
    breadth_score: float = 0.0
    advancers: int = 0
    decliners: int = 0
    unchanged: int = 0
    new_highs: int = 0
    new_lows: int = 0
    percent_above_20d_ma: float = 0.0
    percent_above_50d_ma: float = 0.0
    percent_above_200d_ma: float = 0.0
    up_volume: float = 0.0
    down_volume: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WatchlistContextItem:
    """One watchlist insight prepared for committee context."""

    symbol: str
    summary: str
    bullish_factors: tuple[str, ...] = field(default_factory=tuple)
    bearish_factors: tuple[str, ...] = field(default_factory=tuple)
    open_questions: tuple[str, ...] = field(default_factory=tuple)
    recommended_action: str | None = None


@dataclass(frozen=True)
class WatchlistContextSnapshot:
    """Active watchlist insights available to a context assembly."""

    source: str
    fetched_at: datetime | None = None
    items: tuple[WatchlistContextItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class KnowledgeBaseSnapshot:
    """Remembered research context loaded before committee reasoning."""

    source: str = "knowledge_base"
    fetched_at: datetime | None = None
    thesis: tuple[str, ...] = field(default_factory=tuple)
    discussions: tuple[str, ...] = field(default_factory=tuple)
    research_notes: tuple[str, ...] = field(default_factory=tuple)
    lessons_learned: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ContextMetadata:
    """Metadata describing how context was assembled."""

    generated_at: datetime | None = None
    sources: tuple[str, ...] = field(default_factory=tuple)
    data_quality_notes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MeetingContext:
    """Complete context provided to the committee before reasoning."""

    request: ContextRequest
    metadata: ContextMetadata = field(default_factory=ContextMetadata)
    market: MarketSnapshot | None = None
    news: NewsContext | None = None
    filings: FilingSnapshot | None = None
    financials: FinancialStatementSnapshot | None = None
    valuation: ValuationContextSnapshot | None = None
    portfolio: PortfolioSnapshot | None = None
    macro: MacroSnapshot | None = None
    economic_regime: EconomicRegimeContextSnapshot | None = None
    sector_rotation: SectorRotationContextSnapshot | None = None
    market_breadth: MarketBreadthContextSnapshot | None = None
    watchlist: WatchlistContextSnapshot | None = None
    knowledge_base: KnowledgeBaseSnapshot | None = None
