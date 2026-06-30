"""Macro context provider backed by the Macro Data Layer service boundary."""

from __future__ import annotations

from datetime import datetime, time

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    MacroSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.macro.models import MacroObservation, MacroSeries
from parakeetnest.macro.service import MacroDataService


class MacroContextProvider:
    """Build factual macro context from provider-neutral macro data snapshots."""

    provider_name = "macro"

    _SECTIONS = (
        ("Interest Rates", ("fed_funds_rate", "treasury_10y_yield")),
        ("Inflation", ("cpi_yoy", "core_cpi_yoy")),
        ("Labor Market", ("unemployment_rate", "nonfarm_payrolls")),
        ("Growth", ("gdp_growth",)),
    )

    def __init__(self, macro_data_service: MacroDataService) -> None:
        self._macro_data_service = macro_data_service

    def supports(self, request: ContextRequest) -> bool:
        return request.include_macro

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        as_of_date = request.as_of.date() if request.as_of is not None else None
        snapshot = self._macro_data_service.get_snapshot(
            list(self._indicator_ids()),
            as_of_date=as_of_date,
        )
        indicators = self._render_indicators(snapshot.series)
        fetched_at = request.as_of or datetime.combine(
            snapshot.as_of_date,
            time.min,
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
                data_quality_notes=tuple(snapshot.notes),
            ),
            macro=MacroSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                indicators=indicators,
                observed_on=snapshot.as_of_date,
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "macro_data_service"},
        )

    @classmethod
    def _indicator_ids(cls) -> tuple[str, ...]:
        return tuple(
            indicator_id
            for _, indicator_ids in cls._SECTIONS
            for indicator_id in indicator_ids
        )

    @classmethod
    def _render_indicators(cls, series: list[MacroSeries]) -> tuple[str, ...]:
        series_by_id = {
            item.indicator.indicator_id: item
            for item in sorted(series, key=lambda item: item.indicator.indicator_id)
        }
        lines: list[str] = []

        for section_name, indicator_ids in cls._SECTIONS:
            lines.append(f"{section_name}:")
            for indicator_id in indicator_ids:
                macro_series = series_by_id.get(indicator_id)
                if macro_series is None:
                    lines.append(f"{indicator_id}: no observation available")
                    continue
                lines.append(cls._render_series(macro_series))

        return tuple(lines)

    @classmethod
    def _render_series(cls, series: MacroSeries) -> str:
        observation = cls._latest_observation(series)
        if observation is None:
            return (
                f"{series.indicator.name} ({series.indicator.indicator_id}): "
                "no observation available"
            )

        value = cls._format_observation_value(observation)
        return (
            f"{series.indicator.name} ({series.indicator.indicator_id}, "
            f"{series.indicator.region or 'region_unknown'}, "
            f"{series.indicator.frequency.value}, {series.indicator.unit.value}): "
            f"{value} as of {observation.period.isoformat()}"
        )

    @staticmethod
    def _latest_observation(series: MacroSeries) -> MacroObservation | None:
        if not series.observations:
            return None
        return series.observations[-1]

    @staticmethod
    def _format_observation_value(observation: MacroObservation) -> str:
        if observation.value is None:
            return "None"
        return f"{observation.value:g}"
