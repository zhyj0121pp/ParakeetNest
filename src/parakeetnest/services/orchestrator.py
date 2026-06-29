"""Data collection orchestration for mock services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from parakeetnest.database.models import (
    CalendarEvent,
    FinancialData,
    Holding,
    MacroData,
    MarketData,
    NewsItem,
)
from parakeetnest.domain import (
    CalendarSnapshot,
    FinancialSnapshot,
    MacroSnapshot,
    MarketSnapshot,
    NewsSnapshot,
    PortfolioSnapshot,
)
from parakeetnest.services.base import DataService, ServiceResult
from parakeetnest.services.calendar import MockCalendarService
from parakeetnest.services.data_quality import DataQualityService
from parakeetnest.services.financial import MockFinancialService
from parakeetnest.services.macro import MockMacroService
from parakeetnest.services.market_data import MockMarketDataService
from parakeetnest.services.news import MockNewsService
from parakeetnest.services.portfolio import MockPortfolioService


@dataclass(frozen=True)
class DataCollectionResult:
    """Summary of one deterministic data collection run."""

    results: tuple[ServiceResult[Any], ...]
    saved_records: int


class DataCollectionOrchestrator:
    """Run data services, validate snapshots, and persist valid records."""

    def __init__(
        self,
        services: tuple[DataService[Any], ...] | None = None,
        data_quality_service: DataQualityService | None = None,
    ) -> None:
        """Initialize the orchestrator with mock services by default."""
        self.data_quality_service = data_quality_service or DataQualityService()
        self.services = services or (
            MockPortfolioService(self.data_quality_service),
            MockMarketDataService(self.data_quality_service),
            MockNewsService(self.data_quality_service),
            MockFinancialService(self.data_quality_service),
            MockMacroService(self.data_quality_service),
            MockCalendarService(self.data_quality_service),
        )

    def run(self, session: Session, now: datetime | None = None) -> DataCollectionResult:
        """Collect from all services, validate snapshots, and save valid records."""
        collected: list[ServiceResult[Any]] = []
        saved_records = 0
        for service in self.services:
            for service_result in service.collect():
                snapshot = service_result.snapshot
                validation_time = now or getattr(snapshot, "fetched_at", None)
                data_quality = self.data_quality_service.validate(
                    snapshot,
                    now=validation_time,
                )
                validated_result = ServiceResult(
                    snapshot=snapshot,
                    data_quality=data_quality,
                )
                collected.append(validated_result)
                if data_quality.is_valid:
                    saved_records += self._save_snapshot(session, snapshot)
        session.flush()
        return DataCollectionResult(results=tuple(collected), saved_records=saved_records)

    def _save_snapshot(self, session: Session, snapshot: object) -> int:
        """Persist one validated snapshot and return the number of records saved."""
        if isinstance(snapshot, PortfolioSnapshot):
            for holding in snapshot.holdings:
                session.add(
                    Holding(
                        symbol=holding.symbol,
                        quantity=holding.quantity,
                        cost_basis=holding.cost_basis,
                        market_value=holding.market_value,
                        source=snapshot.source,
                        observed_at=snapshot.fetched_at,
                    )
                )
            return len(snapshot.holdings)
        if isinstance(snapshot, MarketSnapshot):
            session.add(
                MarketData(
                    symbol=snapshot.symbol,
                    price=snapshot.price,
                    daily_change=snapshot.daily_change,
                    volume=snapshot.volume,
                    market_cap=snapshot.market_cap,
                    pe_ratio=snapshot.pe_ratio,
                    eps=snapshot.eps,
                    source=snapshot.source,
                    observed_at=snapshot.fetched_at,
                )
            )
            return 1
        if isinstance(snapshot, FinancialSnapshot):
            session.add(
                FinancialData(
                    symbol=snapshot.symbol,
                    period=snapshot.period,
                    revenue=snapshot.revenue,
                    eps=snapshot.eps,
                    gross_margin=snapshot.gross_margin,
                    operating_margin=snapshot.operating_margin,
                    free_cash_flow=snapshot.free_cash_flow,
                    source=snapshot.source,
                    observed_at=snapshot.fetched_at,
                )
            )
            return 1
        if isinstance(snapshot, NewsSnapshot):
            session.add(
                NewsItem(
                    symbol=snapshot.symbol,
                    title=snapshot.title,
                    url=snapshot.url,
                    source=snapshot.source,
                    summary=snapshot.summary,
                    published_at=snapshot.published_at,
                )
            )
            return 1
        if isinstance(snapshot, MacroSnapshot):
            session.add(
                MacroData(
                    indicator=snapshot.indicator,
                    value=snapshot.value,
                    unit=snapshot.unit,
                    source=snapshot.source,
                    observed_on=snapshot.observed_on,
                )
            )
            return 1
        if isinstance(snapshot, CalendarSnapshot):
            session.add(
                CalendarEvent(
                    event_type=snapshot.event_type,
                    title=snapshot.title,
                    symbol=snapshot.symbol,
                    event_at=snapshot.event_at,
                    source=snapshot.source,
                )
            )
            return 1
        return 0
