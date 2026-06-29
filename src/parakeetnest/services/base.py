"""Base interfaces and result types for data services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from parakeetnest.domain import (
    CalendarSnapshot,
    FinancialSnapshot,
    MacroSnapshot,
    MarketSnapshot,
    NewsSnapshot,
    PortfolioSnapshot,
)
from parakeetnest.services.data_quality import DataQuality, DataQualityService


SnapshotT = TypeVar(
    "SnapshotT",
    PortfolioSnapshot,
    MarketSnapshot,
    FinancialSnapshot,
    NewsSnapshot,
    MacroSnapshot,
    CalendarSnapshot,
)


@dataclass(frozen=True)
class ServiceResult(Generic[SnapshotT]):
    """A normalized service snapshot plus its data quality metadata."""

    snapshot: SnapshotT
    data_quality: DataQuality


class DataService(Protocol[SnapshotT]):
    """Base protocol for deterministic and future data service implementations."""

    name: str

    def collect(self) -> tuple[ServiceResult[SnapshotT], ...]:
        """Collect normalized snapshots with data quality metadata."""


class PortfolioService(DataService[PortfolioSnapshot], Protocol):
    """Protocol for portfolio data collection services."""


class MarketDataService(DataService[MarketSnapshot], Protocol):
    """Protocol for market data collection services."""


class NewsService(DataService[NewsSnapshot], Protocol):
    """Protocol for news data collection services."""


class FinancialService(DataService[FinancialSnapshot], Protocol):
    """Protocol for financial data collection services."""


class MacroService(DataService[MacroSnapshot], Protocol):
    """Protocol for macro data collection services."""


class CalendarService(DataService[CalendarSnapshot], Protocol):
    """Protocol for calendar data collection services."""


class SnapshotPersistence(Protocol):
    """Protocol for persistence adapters that store validated snapshots."""

    def save(self, snapshot: object, data_quality: DataQuality) -> int:
        """Persist a validated snapshot and return the number of records saved."""


class MockDataService(Generic[SnapshotT]):
    """Base helper for deterministic mock data services."""

    name: str

    def __init__(self, data_quality_service: DataQualityService | None = None) -> None:
        """Initialize the mock service with a data quality service."""
        self.data_quality_service = data_quality_service or DataQualityService()

    def _result(self, snapshot: SnapshotT) -> ServiceResult[SnapshotT]:
        """Attach data quality metadata to a deterministic snapshot."""
        return ServiceResult(
            snapshot=snapshot,
            data_quality=self.data_quality_service.validate(
                snapshot,
                now=snapshot.fetched_at,
            ),
        )
