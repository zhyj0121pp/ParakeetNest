"""Sector rotation context provider backed by the service boundary."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Protocol

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MeetingContext,
    SectorRotationContextSnapshot,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.intelligence.sector_rotation.models import (
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)


class _SectorRotationService(Protocol):
    """Minimal sector rotation service contract consumed by the provider."""

    def get_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        """Return the current provider-neutral sector rotation snapshot."""


class SectorRotationContextProvider:
    """Build prompt-ready sector rotation context from service snapshots."""

    provider_name = "sector_rotation"

    def __init__(self, sector_rotation_service: _SectorRotationService) -> None:
        self._sector_rotation_service = sector_rotation_service

    def supports(self, request: ContextRequest) -> bool:
        return request.include_macro

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        as_of_date = request.as_of.date() if request.as_of is not None else None
        snapshot = self._sector_rotation_service.get_snapshot(as_of_date=as_of_date)
        fetched_at = request.as_of or datetime.combine(snapshot.as_of_date, time.min)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            sector_rotation=SectorRotationContextSnapshot(
                source=snapshot.source or self.provider_name,
                fetched_at=fetched_at,
                as_of_date=snapshot.as_of_date,
                summary=snapshot.summary,
                leaders=self._sector_names(
                    snapshot.signals,
                    SectorRotationClassification.LEADING,
                ),
                improving=self._sector_names(
                    snapshot.signals,
                    SectorRotationClassification.IMPROVING,
                ),
                weakening=self._sector_names(
                    snapshot.signals,
                    SectorRotationClassification.WEAKENING,
                ),
                laggards=self._sector_names(
                    snapshot.signals,
                    SectorRotationClassification.LAGGING,
                ),
                unknown=self._unknown_sector_names(snapshot.signals),
                evidence=self._render_evidence(snapshot.signals),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "sector_rotation_service"},
        )

    @staticmethod
    def _sector_names(
        signals: list[SectorRotationSignal],
        classification: SectorRotationClassification,
    ) -> tuple[str, ...]:
        return tuple(
            signal.sector.name
            for signal in signals
            if signal.classification is classification
        )

    @staticmethod
    def _unknown_sector_names(
        signals: list[SectorRotationSignal],
    ) -> tuple[str, ...]:
        return tuple(
            signal.sector.name
            for signal in signals
            if signal.classification
            in {
                SectorRotationClassification.NEUTRAL,
                SectorRotationClassification.UNKNOWN,
            }
        )

    @staticmethod
    def _render_evidence(signals: list[SectorRotationSignal]) -> tuple[str, ...]:
        evidence_lines: list[str] = []
        for signal in signals:
            evidence_lines.extend(
                f"{signal.sector.name}: {item}" for item in signal.evidence
            )
        return tuple(evidence_lines)


__all__ = ["SectorRotationContextProvider"]
