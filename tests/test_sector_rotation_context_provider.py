"""Tests for SectorRotationContextProvider service-backed context generation."""

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
from parakeetnest.intelligence.sector_rotation import (
    SectorIdentifier,
    SectorRotationClassification,
    SectorRotationSignal,
    SectorRotationSnapshot,
)
from parakeetnest.intelligence.sector_rotation.context_provider import (
    SectorRotationContextProvider,
)


AS_OF_DATE = date(2026, 6, 30)


class RecordingSectorRotationService:
    """Sector rotation service test double that records provider calls."""

    def __init__(self, snapshot: SectorRotationSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[date | None] = []

    def get_snapshot(
        self,
        *,
        as_of_date: date | None = None,
    ) -> SectorRotationSnapshot:
        self.calls.append(as_of_date)
        return self.snapshot


def sector_rotation_snapshot(
    *,
    signals: list[SectorRotationSignal] | None = None,
    summary: str | None = "Leadership is concentrated in cyclical sectors.",
    source: str | None = "sector_rotation_calculator",
) -> SectorRotationSnapshot:
    """Build a provider-neutral sector rotation snapshot for context tests."""
    return SectorRotationSnapshot(
        as_of_date=AS_OF_DATE,
        signals=signals
        if signals is not None
        else [
            SectorRotationSignal(
                sector=SectorIdentifier(sector_id="energy", name="Energy"),
                classification=SectorRotationClassification.LEADING,
                confidence="high",
                evidence=("Relative return classified as leading.",),
            ),
            SectorRotationSignal(
                sector=SectorIdentifier(sector_id="industrials", name="Industrials"),
                classification=SectorRotationClassification.IMPROVING,
                confidence="medium",
                evidence=("Relative return classified as improving.",),
            ),
            SectorRotationSignal(
                sector=SectorIdentifier(sector_id="utilities", name="Utilities"),
                classification=SectorRotationClassification.WEAKENING,
                confidence="high",
                evidence=("Relative return classified as weakening.",),
            ),
            SectorRotationSignal(
                sector=SectorIdentifier(sector_id="real-estate", name="Real Estate"),
                classification=SectorRotationClassification.LAGGING,
                confidence="high",
                evidence=("Relative return classified as lagging.",),
            ),
            SectorRotationSignal(
                sector=SectorIdentifier(sector_id="materials", name="Materials"),
                classification=SectorRotationClassification.UNKNOWN,
                confidence="low",
                evidence=("Relative performance evidence is incomplete.",),
            ),
        ],
        summary=summary,
        source=source,
    )


def test_sector_rotation_context_provider_builds_prompt_neutral_context() -> None:
    service = RecordingSectorRotationService(sector_rotation_snapshot())
    provider = SectorRotationContextProvider(service)
    request = ContextRequest(
        question="Review AMD sector context.",
        symbols=("AMD",),
        as_of=datetime(2026, 6, 30, 14, 0, tzinfo=UTC),
    )

    result = provider.build_context(request)

    assert service.calls == [AS_OF_DATE]
    assert result.provider_name == "sector_rotation"
    assert result.metadata == {"source": "sector_rotation_service"}
    assert result.partial_context.metadata.sources == ("sector_rotation",)
    assert result.partial_context.sector_rotation is not None
    assert result.partial_context.sector_rotation.source == (
        "sector_rotation_calculator"
    )
    assert result.partial_context.sector_rotation.as_of_date == AS_OF_DATE
    assert result.partial_context.sector_rotation.summary == (
        "Leadership is concentrated in cyclical sectors."
    )
    assert result.partial_context.sector_rotation.leaders == ("Energy",)
    assert result.partial_context.sector_rotation.improving == ("Industrials",)
    assert result.partial_context.sector_rotation.weakening == ("Utilities",)
    assert result.partial_context.sector_rotation.laggards == ("Real Estate",)
    assert result.partial_context.sector_rotation.unknown == ("Materials",)
    assert result.partial_context.sector_rotation.evidence == (
        "Energy: Relative return classified as leading.",
        "Industrials: Relative return classified as improving.",
        "Materials: Relative performance evidence is incomplete.",
        "Real Estate: Relative return classified as lagging.",
        "Utilities: Relative return classified as weakening.",
    )


def test_sector_rotation_context_provider_handles_empty_snapshot() -> None:
    provider = SectorRotationContextProvider(
        RecordingSectorRotationService(sector_rotation_snapshot(signals=[]))
    )

    context = ContextService(providers=(provider,)).build_context(
        ContextRequest(question="Review sector rotation.", symbols=())
    )
    rendered = MeetingContextPromptRenderer().render(context)

    assert context.sector_rotation is not None
    assert context.sector_rotation.leaders == ()
    assert "- Leading sectors: None" in rendered
    assert "- Evidence: None" in rendered


def test_sector_rotation_context_provider_supports_include_macro_only() -> None:
    provider = SectorRotationContextProvider(
        RecordingSectorRotationService(sector_rotation_snapshot())
    )
    supported = ContextRequest(question="Review AMD.", symbols=("AMD",))
    unsupported = ContextRequest(
        question="Review AMD without macro context.",
        symbols=("AMD",),
        include_macro=False,
    )

    assert provider.supports(supported) is True
    assert provider.supports(unsupported) is False
    with pytest.raises(UnsupportedContextRequestError, match="sector_rotation"):
        provider.build_context(unsupported)


def test_sector_rotation_context_provider_is_provider_neutral() -> None:
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "llm",
        "sectorrotationprovider",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(
        sys.modules[SectorRotationContextProvider.__module__]
    ).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider = SectorRotationContextProvider(
        RecordingSectorRotationService(sector_rotation_snapshot())
    )

    assert provider.build_context(ContextRequest(question="Review sectors.", symbols=()))
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_create_app_registers_sector_rotation_context_provider(tmp_path) -> None:
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

    assert isinstance(registrations["sector_rotation"], SectorRotationContextProvider)
    assert context.sector_rotation is not None
