"""Tests for deterministic mock data services and orchestration."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from parakeetnest.database import create_sqlite_engine, initialize_database
from parakeetnest.database.models import (
    CalendarEvent,
    DataQualityReport,
    FinancialData,
    Holding,
    MacroData,
    MarketData,
    NewsItem,
)
from parakeetnest.database.snapshot_repository import SnapshotPersistenceService
from parakeetnest.domain import MarketSnapshot
from parakeetnest.services import (
    DataCollectionOrchestrator,
    MockCalendarService,
    MockFinancialService,
    MockMacroService,
    MockMarketDataService,
    MockNewsService,
    MockPortfolioService,
    ServiceResult,
)
from parakeetnest.services.data_quality import DataQualityService
from parakeetnest.services.portfolio import MOCK_FETCHED_AT


def test_mock_services_return_valid_typed_snapshots() -> None:
    """Every mock service should return deterministic valid service results."""
    services = (
        MockPortfolioService(),
        MockMarketDataService(),
        MockNewsService(),
        MockFinancialService(),
        MockMacroService(),
        MockCalendarService(),
    )

    for service in services:
        results = service.collect()

        assert results
        assert all(result.data_quality.is_valid for result in results)
        assert all(result.snapshot.source == service.name for result in results)


def test_orchestrator_saves_valid_mock_data(tmp_path: Path) -> None:
    """The orchestrator should persist validated mock snapshots to SQLite."""
    engine = create_sqlite_engine(tmp_path / "mock_collection.sqlite3")
    initialize_database(engine)

    with Session(engine) as session:
        persistence = SnapshotPersistenceService(session)
        result = DataCollectionOrchestrator().run(persistence, now=MOCK_FETCHED_AT)
        session.commit()

        assert len(result.results) == 11
        assert result.saved_records == 12
        assert all(item.data_quality.is_valid for item in result.results)
        assert len(session.scalars(select(Holding)).all()) == 2
        assert len(session.scalars(select(MarketData)).all()) == 2
        assert len(session.scalars(select(NewsItem)).all()) == 2
        assert len(session.scalars(select(FinancialData)).all()) == 2
        assert len(session.scalars(select(MacroData)).all()) == 2
        assert len(session.scalars(select(CalendarEvent)).all()) == 2
        reports = session.scalars(select(DataQualityReport)).all()
        assert len(reports) == 11
        assert {report.validation_status for report in reports} == {"valid"}


def test_orchestrator_skips_invalid_snapshots(tmp_path: Path) -> None:
    """Invalid snapshots should be reported but not persisted."""

    class InvalidMarketService:
        """Small invalid service for orchestrator behavior testing."""

        name = "invalid_market"

        def collect(self) -> tuple[ServiceResult[MarketSnapshot], ...]:
            snapshot = MarketSnapshot(
                source=self.name,
                fetched_at=MOCK_FETCHED_AT,
                symbol="BAD",
                price=-1.0,
            )
            return (
                ServiceResult(
                    snapshot=snapshot,
                    data_quality=DataQualityService().validate(
                        snapshot,
                        now=MOCK_FETCHED_AT,
                    ),
                ),
            )

    engine = create_sqlite_engine(tmp_path / "invalid_collection.sqlite3")
    initialize_database(engine)

    with Session(engine) as session:
        persistence = SnapshotPersistenceService(session)
        result = DataCollectionOrchestrator(
            services=(InvalidMarketService(),),
        ).run(persistence, now=MOCK_FETCHED_AT)
        session.commit()

        assert len(result.results) == 1
        assert result.results[0].data_quality.is_valid is False
        assert result.saved_records == 0
        assert len(session.scalars(select(MarketData)).all()) == 0
        assert len(session.scalars(select(DataQualityReport)).all()) == 0


def test_mock_data_is_deterministic() -> None:
    """Repeated mock service calls should produce equal snapshots."""
    first = MockMarketDataService().collect()
    second = MockMarketDataService().collect()

    assert first == second
    assert first[0].snapshot.fetched_at == datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
