"""Tests for EconomicRegimeContextProvider service-backed context generation."""

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
from parakeetnest.regime import (
    EconomicRegime,
    EconomicRegimeSnapshot,
    RegimeConfidence,
    RegimeIndicator,
    RegimeSignal,
)
from parakeetnest.regime.context_provider import EconomicRegimeContextProvider


AS_OF_DATE = date(2026, 6, 30)


class RecordingEconomicRegimeService:
    """Regime service test double that records context-provider calls."""

    def __init__(self, snapshot: EconomicRegimeSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[date | None] = []

    def get_current_regime(
        self,
        *,
        as_of_date: date | None = None,
    ) -> EconomicRegimeSnapshot:
        self.calls.append(as_of_date)
        return self.snapshot


def regime_snapshot(
    *,
    regime: EconomicRegime = EconomicRegime.EXPANSION,
    confidence: RegimeConfidence = RegimeConfidence.HIGH,
    indicators: list[RegimeIndicator] | None = None,
    summary: str | None = "Growth is firm while inflation is cooling.",
    source: str | None = "economic_regime_service",
) -> EconomicRegimeSnapshot:
    """Build a provider-neutral regime snapshot for context tests."""
    return EconomicRegimeSnapshot(
        regime=regime,
        confidence=confidence,
        as_of_date=AS_OF_DATE,
        indicators=indicators
        if indicators is not None
        else [
            RegimeIndicator(
                signal=RegimeSignal.GROWTH,
                name="GDP Growth",
                value=2.4,
                unit="percent",
                as_of_date=AS_OF_DATE,
                interpretation="growth remains above trend",
            ),
            RegimeIndicator(
                signal=RegimeSignal.INFLATION,
                name="CPI Year-over-Year",
                value=2.6,
                unit="percent",
                as_of_date=AS_OF_DATE,
                interpretation="inflation is moderating",
            ),
        ],
        summary=summary,
        source=source,
    )


def test_regime_context_provider_renders_normal_snapshot() -> None:
    service = RecordingEconomicRegimeService(regime_snapshot())
    provider = EconomicRegimeContextProvider(service)
    request = ContextRequest(
        question="Review AMD regime context.",
        symbols=("AMD",),
        as_of=datetime(2026, 6, 30, 14, 0, tzinfo=UTC),
    )

    result = provider.build_context(request)

    assert service.calls == [AS_OF_DATE]
    assert result.provider_name == "economic_regime"
    assert result.metadata == {"source": "economic_regime_service"}
    assert result.partial_context.metadata.sources == ("economic_regime",)
    assert result.partial_context.economic_regime is not None
    assert result.partial_context.economic_regime.regime == "expansion"
    assert result.partial_context.economic_regime.confidence == "high"
    assert result.partial_context.economic_regime.observed_on == AS_OF_DATE
    assert result.partial_context.economic_regime.summary == (
        "Growth is firm while inflation is cooling."
    )
    assert result.partial_context.economic_regime.regime_source == (
        "economic_regime_service"
    )
    assert result.partial_context.economic_regime.indicators == (
        "CPI Year-over-Year (inflation): 2.6 percent, as of 2026-06-30, "
        "inflation is moderating",
        "GDP Growth (growth): 2.4 percent, as of 2026-06-30, "
        "growth remains above trend",
    )


def test_regime_context_provider_handles_unknown_regime_gracefully() -> None:
    service = RecordingEconomicRegimeService(
        regime_snapshot(
            regime=EconomicRegime.UNKNOWN,
            confidence=RegimeConfidence.UNKNOWN,
            indicators=[],
            summary="Unable to determine the current economic regime.",
            source=None,
        )
    )
    provider = EconomicRegimeContextProvider(service)

    context = ContextService(providers=(provider,)).build_context(
        ContextRequest(question="Review macro.", symbols=())
    )
    rendered = MeetingContextPromptRenderer().render(context)

    assert context.economic_regime is not None
    assert context.economic_regime.regime == "unknown"
    assert context.economic_regime.confidence == "unknown"
    assert "- Current regime: unknown" in rendered
    assert "- Confidence: unknown" in rendered
    assert "- Supporting indicators: None" in rendered


def test_regime_context_provider_supports_empty_indicators() -> None:
    provider = EconomicRegimeContextProvider(
        RecordingEconomicRegimeService(regime_snapshot(indicators=[]))
    )

    result = provider.build_context(
        ContextRequest(question="Review regime.", symbols=())
    )

    assert result.partial_context.economic_regime is not None
    assert result.partial_context.economic_regime.indicators == ()


def test_regime_context_provider_invokes_service_once_per_build() -> None:
    service = RecordingEconomicRegimeService(regime_snapshot())
    provider = EconomicRegimeContextProvider(service)
    request = ContextRequest(question="Review regime.", symbols=())

    provider.build_context(request)
    provider.build_context(request)

    assert service.calls == [None, None]


def test_regime_context_provider_output_formatting() -> None:
    provider = EconomicRegimeContextProvider(
        RecordingEconomicRegimeService(regime_snapshot())
    )
    context = ContextService(providers=(provider,)).build_context(
        ContextRequest(
            question="Review regime.",
            symbols=(),
            as_of=datetime(2026, 6, 30, 14, 0, tzinfo=UTC),
        )
    )

    rendered = MeetingContextPromptRenderer().render(context)

    assert "## Economic Regime" in rendered
    assert "- Snapshot: source=economic_regime" in rendered
    assert "- Current regime: expansion" in rendered
    assert "- Confidence: high" in rendered
    assert "- Summary: Growth is firm while inflation is cooling." in rendered
    assert "- Source: economic_regime_service" in rendered
    assert "- Supporting indicators:" in rendered
    assert "GDP Growth (growth): 2.4 percent" in rendered


def test_regime_context_provider_supports_include_macro_only() -> None:
    provider = EconomicRegimeContextProvider(
        RecordingEconomicRegimeService(regime_snapshot())
    )
    supported = ContextRequest(question="Review AMD.", symbols=("AMD",))
    unsupported = ContextRequest(
        question="Review AMD without macro.",
        symbols=("AMD",),
        include_macro=False,
    )

    assert provider.supports(supported) is True
    assert provider.supports(unsupported) is False
    with pytest.raises(UnsupportedContextRequestError, match="economic_regime"):
        provider.build_context(unsupported)


def test_regime_context_provider_is_provider_neutral() -> None:
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
        "macrodataprovider",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(
        sys.modules[EconomicRegimeContextProvider.__module__]
    ).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = EconomicRegimeContextProvider(
        RecordingEconomicRegimeService(regime_snapshot())
    )

    assert provider.build_context(ContextRequest(question="Review regime.", symbols=()))
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_create_app_registers_regime_context_provider(tmp_path) -> None:
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

    assert isinstance(registrations["economic_regime"], EconomicRegimeContextProvider)
    assert context.economic_regime is not None
    assert context.economic_regime.source == "economic_regime"
