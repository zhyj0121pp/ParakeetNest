"""Data collection orchestration for mock services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from parakeetnest.services.base import DataService, ServiceResult, SnapshotPersistence
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

    def run(
        self,
        persistence: SnapshotPersistence,
        now: datetime | None = None,
    ) -> DataCollectionResult:
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
                    saved_records += persistence.save(snapshot, data_quality)
        return DataCollectionResult(results=tuple(collected), saved_records=saved_records)
