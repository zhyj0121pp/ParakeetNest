"""Tests for MacroContextProvider service-backed context generation."""

from __future__ import annotations

import inspect
import sys
from datetime import UTC, date, datetime

import pytest

from parakeetnest.app import create_app
from parakeetnest.config import AppConfig
from parakeetnest.context import (
    ContextRequest,
    ContextService,
    MeetingContextPromptRenderer,
    UnsupportedContextRequestError,
)
from parakeetnest.context.providers import MacroContextProvider
from parakeetnest.macro import (
    MacroCategory,
    MacroDataService,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)


class RecordingMacroDataService(MacroDataService):
    """MacroDataService test double with deterministic provider-neutral data."""

    def __init__(self) -> None:
        self.snapshot_calls: list[tuple[list[str], date | None]] = []
        self.snapshot = MacroSnapshot(
            as_of_date=date(2026, 6, 30),
            series=[
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="gdp_growth",
                        name="GDP Growth",
                        category=MacroCategory.GROWTH,
                        frequency=MacroFrequency.QUARTERLY,
                        unit=MacroUnit.PERCENT,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 3, 31), value=2.0),
                        MacroObservation(period=date(2026, 6, 30), value=1.9),
                    ],
                ),
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="fed_funds_rate",
                        name="Federal Funds Rate",
                        category=MacroCategory.RATES,
                        frequency=MacroFrequency.MONTHLY,
                        unit=MacroUnit.PERCENT,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 6, 30), value=4.0),
                    ],
                ),
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="treasury_10y_yield",
                        name="10-Year Treasury Yield",
                        category=MacroCategory.RATES,
                        frequency=MacroFrequency.MONTHLY,
                        unit=MacroUnit.PERCENT,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 6, 30), value=4.08),
                    ],
                ),
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="cpi_yoy",
                        name="CPI Year-over-Year",
                        category=MacroCategory.INFLATION,
                        frequency=MacroFrequency.MONTHLY,
                        unit=MacroUnit.PERCENT,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 6, 30), value=2.7),
                    ],
                ),
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="core_cpi_yoy",
                        name="Core CPI Year-over-Year",
                        category=MacroCategory.INFLATION,
                        frequency=MacroFrequency.MONTHLY,
                        unit=MacroUnit.PERCENT,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 6, 30), value=3.0),
                    ],
                ),
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="unemployment_rate",
                        name="Unemployment Rate",
                        category=MacroCategory.LABOR,
                        frequency=MacroFrequency.MONTHLY,
                        unit=MacroUnit.PERCENT,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 6, 30), value=4.3),
                    ],
                ),
                MacroSeries(
                    indicator=MacroIndicator(
                        indicator_id="nonfarm_payrolls",
                        name="Nonfarm Payrolls",
                        category=MacroCategory.LABOR,
                        frequency=MacroFrequency.MONTHLY,
                        unit=MacroUnit.THOUSANDS,
                        region="US",
                    ),
                    observations=[
                        MacroObservation(period=date(2026, 6, 30), value=129.0),
                    ],
                ),
            ],
            notes=["provider-neutral fixture"],
        )

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        self.snapshot_calls.append((indicator_ids, as_of_date))
        return self.snapshot


def test_macro_context_provider_generates_factual_sections() -> None:
    service = RecordingMacroDataService()
    provider = MacroContextProvider(service)
    request = ContextRequest(
        question="Review AMD macro context.",
        symbols=("AMD",),
        as_of=datetime(2026, 6, 30, 14, 0, tzinfo=UTC),
    )

    result = provider.build_context(request)

    assert service.snapshot_calls == [
        (
            [
                "fed_funds_rate",
                "treasury_10y_yield",
                "cpi_yoy",
                "core_cpi_yoy",
                "unemployment_rate",
                "nonfarm_payrolls",
                "gdp_growth",
            ],
            date(2026, 6, 30),
        )
    ]
    assert result.provider_name == "macro"
    assert result.partial_context.metadata.sources == ("macro",)
    assert result.metadata == {"source": "macro_data_service"}
    assert result.partial_context.macro is not None
    assert result.partial_context.macro.summary is None
    assert result.partial_context.macro.indicators == (
        "Interest Rates:",
        "Federal Funds Rate (fed_funds_rate, US, monthly, percent): "
        "4 as of 2026-06-30",
        "10-Year Treasury Yield (treasury_10y_yield, US, monthly, percent): "
        "4.08 as of 2026-06-30",
        "Inflation:",
        "CPI Year-over-Year (cpi_yoy, US, monthly, percent): "
        "2.7 as of 2026-06-30",
        "Core CPI Year-over-Year (core_cpi_yoy, US, monthly, percent): "
        "3 as of 2026-06-30",
        "Labor Market:",
        "Unemployment Rate (unemployment_rate, US, monthly, percent): "
        "4.3 as of 2026-06-30",
        "Nonfarm Payrolls (nonfarm_payrolls, US, monthly, thousands): "
        "129 as of 2026-06-30",
        "Growth:",
        "GDP Growth (gdp_growth, US, quarterly, percent): 1.9 as of 2026-06-30",
    )


def test_macro_context_provider_supports_include_macro_only() -> None:
    provider = MacroContextProvider(RecordingMacroDataService())
    supported = ContextRequest(question="Review AMD.", symbols=("AMD",))
    unsupported = ContextRequest(
        question="Review AMD without macro.",
        symbols=("AMD",),
        include_macro=False,
    )

    assert provider.supports(supported) is True
    assert provider.supports(unsupported) is False
    with pytest.raises(UnsupportedContextRequestError, match="macro"):
        provider.build_context(unsupported)


def test_macro_context_provider_output_is_deterministic() -> None:
    provider = MacroContextProvider(RecordingMacroDataService())
    request = ContextRequest(question="Review macro.", symbols=())

    assert provider.build_context(request) == provider.build_context(request)


def test_macro_context_provider_works_with_context_service_and_renderer() -> None:
    request = ContextRequest(question="Review macro.", symbols=())
    context = ContextService(
        providers=(MacroContextProvider(RecordingMacroDataService()),)
    ).build_context(request)
    rendered = MeetingContextPromptRenderer().render(context)

    assert context.macro is not None
    assert context.metadata.sources == ("macro",)
    assert "Interest Rates:" in rendered
    assert "Inflation:" in rendered
    assert "Labor Market:" in rendered
    assert "Growth:" in rendered
    assert "recommend" not in rendered.lower()
    assert "outlook" not in rendered.lower()


def test_macro_context_provider_is_network_free_and_provider_neutral() -> None:
    forbidden_names = {
        "fred",
        "yahoo",
        "bea",
        "bls",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "llm",
        "mockmacrodataprovider",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[MacroContextProvider.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = MacroContextProvider(RecordingMacroDataService())

    assert provider.build_context(ContextRequest(question="Review macro.", symbols=()))
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_create_app_registers_macro_context_provider(tmp_path) -> None:
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        registrations = {
            registration.provider_id: registration.provider
            for registration in app.context_provider_registry.list_registrations()
        }
        context = app.context_service.build_context(
            ContextRequest(question="Review AMD.", symbols=("AMD",))
        )
    finally:
        app.close()

    assert isinstance(registrations["macro"], MacroContextProvider)
    assert context.macro is not None
    assert context.macro.source == "macro"
    assert "Interest Rates:" in context.macro.indicators
