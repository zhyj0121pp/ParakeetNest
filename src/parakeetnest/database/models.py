"""SQLAlchemy ORM models for the ParakeetNest v1 SQLite database."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TimestampMixin:
    """Created and updated timestamps for mutable records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Holding(TimestampMixin, Base):
    """Portfolio holding snapshot."""

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    cost_basis: Mapped[float | None] = mapped_column(Float)
    market_value: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WatchlistItem(TimestampMixin, Base):
    """A symbol being watched before or alongside ownership."""

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class MarketData(TimestampMixin, Base):
    """Market data snapshot for one symbol."""

    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    price: Mapped[float | None] = mapped_column(Float)
    daily_change: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    market_cap: Mapped[float | None] = mapped_column(Float)
    pe_ratio: Mapped[float | None] = mapped_column(Float)
    eps: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinancialData(TimestampMixin, Base):
    """Financial data snapshot for one symbol and period."""

    __tablename__ = "financial_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    period: Mapped[str | None] = mapped_column(String(32))
    revenue: Mapped[float | None] = mapped_column(Float)
    eps: Mapped[float | None] = mapped_column(Float)
    gross_margin: Mapped[float | None] = mapped_column(Float)
    operating_margin: Mapped[float | None] = mapped_column(Float)
    free_cash_flow: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NewsItem(TimestampMixin, Base):
    """News item relevant to a company, sector, or macro theme."""

    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MacroData(TimestampMixin, Base):
    """Macro indicator observation."""

    __tablename__ = "macro_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    indicator: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_on: Mapped[date | None] = mapped_column(Date)


class CalendarEvent(TimestampMixin, Base):
    """Investment-relevant calendar event."""

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(16), index=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(64))


class InvestmentThesis(TimestampMixin, Base):
    """Stored investment thesis for a company."""

    __tablename__ = "investment_theses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    catalysts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    invalidation_conditions: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CommitteeDiscussion(TimestampMixin, Base):
    """Stored committee discussion or role-specific memo."""

    __tablename__ = "committee_discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    catalysts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Recommendation(TimestampMixin, Base):
    """Final committee recommendation record."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    horizon: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    catalysts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    data_confidence: Mapped[str] = mapped_column(String(16), nullable=False)


class Report(TimestampMixin, Base):
    """Generated report record."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )
