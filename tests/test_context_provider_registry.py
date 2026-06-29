"""Tests for ContextProviderRegistry behavior."""

from __future__ import annotations

import pytest

from parakeetnest.context import (
    ContextProviderRegistry,
    ContextProviderResult,
    ContextRequest,
    ContextService,
    MeetingContext,
    NewsSnapshot,
)


class RecordingProvider:
    """Provider test double with a stable name and support flag."""

    def __init__(self, provider_name: str, *, supported: bool = True) -> None:
        self.provider_name = provider_name
        self.supported = supported

    def supports(self, request: ContextRequest) -> bool:
        return self.supported

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        partial_context = MeetingContext(
            request=request,
            news=NewsSnapshot(source=self.provider_name),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
        )


def test_registry_registers_and_lists_providers_in_order() -> None:
    registry = ContextProviderRegistry()
    first = RecordingProvider("first")
    second = RecordingProvider("second")

    registry.register("first-provider", first)
    registry.register("second-provider", second, enabled=False)

    assert registry.list_providers() == (first, second)
    assert [
        (registration.provider_id, registration.provider, registration.enabled)
        for registration in registry.list_registrations()
    ] == [
        ("first-provider", first, True),
        ("second-provider", second, False),
    ]


def test_registry_rejects_duplicate_provider_ids() -> None:
    registry = ContextProviderRegistry()
    registry.register("news", RecordingProvider("news_v1"))

    with pytest.raises(ValueError, match="already registered: news"):
        registry.register("news", RecordingProvider("news_v2"))


def test_registry_resolves_only_enabled_providers() -> None:
    registry = ContextProviderRegistry()
    enabled = RecordingProvider("enabled")
    disabled = RecordingProvider("disabled")

    registry.register("enabled", enabled)
    registry.register("disabled", disabled, enabled=False)

    assert registry.resolve_enabled_providers() == (enabled,)

    registry.enable("disabled")
    registry.disable("enabled")

    assert registry.resolve_enabled_providers() == (disabled,)


def test_registry_unknown_provider_toggle_is_clear() -> None:
    registry = ContextProviderRegistry()

    with pytest.raises(KeyError, match="Unknown context provider: missing"):
        registry.disable("missing")


def test_context_service_can_use_resolved_enabled_providers() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    registry = ContextProviderRegistry()
    disabled = RecordingProvider("disabled")
    enabled = RecordingProvider("enabled")
    registry.register("disabled", disabled, enabled=False)
    registry.register("enabled", enabled)

    service = ContextService(providers=registry.resolve_enabled_providers())
    context = service.build_context(request)

    assert context.news == NewsSnapshot(source="enabled")
    assert context.metadata.sources == ()
