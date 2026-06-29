"""Persistence adapter for validated domain snapshots."""

from __future__ import annotations

from sqlalchemy.orm import Session

from parakeetnest.database.models import (
    CalendarEvent,
    DataQualityReport,
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
from parakeetnest.services.data_quality import DataQuality


class SnapshotPersistenceService:
    """Persist validated snapshots and their data quality metadata."""

    def __init__(self, session: Session) -> None:
        """Initialize the persistence service with a database session."""
        self.session = session

    def save(self, snapshot: object, data_quality: DataQuality) -> int:
        """Persist a validated snapshot and return the number of fact records saved."""
        record_ids = self._save_snapshot(snapshot)
        if record_ids:
            self._save_data_quality(snapshot, data_quality, record_ids)
        return len(record_ids)

    def _save_snapshot(self, snapshot: object) -> list[int]:
        """Persist one snapshot and return saved fact record ids."""
        if isinstance(snapshot, PortfolioSnapshot):
            records = [
                Holding(
                    symbol=holding.symbol,
                    quantity=holding.quantity,
                    cost_basis=holding.cost_basis,
                    market_value=holding.market_value,
                    source=snapshot.source,
                    observed_at=snapshot.fetched_at,
                )
                for holding in snapshot.holdings
            ]
            self.session.add_all(records)
            self.session.flush()
            return [record.id for record in records]

        record = self._to_record(snapshot)
        if record is None:
            return []
        self.session.add(record)
        self.session.flush()
        return [record.id]

    def _to_record(self, snapshot: object) -> object | None:
        """Map a supported snapshot to its ORM record."""
        if isinstance(snapshot, MarketSnapshot):
            return MarketData(
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
        if isinstance(snapshot, FinancialSnapshot):
            return FinancialData(
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
        if isinstance(snapshot, NewsSnapshot):
            return NewsItem(
                symbol=snapshot.symbol,
                title=snapshot.title,
                url=snapshot.url,
                source=snapshot.source,
                summary=snapshot.summary,
                published_at=snapshot.published_at,
            )
        if isinstance(snapshot, MacroSnapshot):
            return MacroData(
                indicator=snapshot.indicator,
                value=snapshot.value,
                unit=snapshot.unit,
                source=snapshot.source,
                observed_on=snapshot.observed_on,
            )
        if isinstance(snapshot, CalendarSnapshot):
            return CalendarEvent(
                event_type=snapshot.event_type,
                title=snapshot.title,
                symbol=snapshot.symbol,
                event_at=snapshot.event_at,
                source=snapshot.source,
            )
        return None

    def _save_data_quality(
        self,
        snapshot: object,
        data_quality: DataQuality,
        record_ids: list[int],
    ) -> None:
        """Persist data quality metadata for saved fact records."""
        self.session.add(
            DataQualityReport(
                dataset_type=type(snapshot).__name__,
                record_ids=record_ids,
                source=data_quality.source,
                fetched_at=data_quality.fetched_at,
                freshness_status=data_quality.freshness_status.value,
                missing_fields=list(data_quality.missing_fields),
                validation_status=data_quality.validation_status.value,
                confidence_score=data_quality.confidence_score,
            )
        )
