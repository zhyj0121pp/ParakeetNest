"""Tests for Context Layer provider abstractions."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from parakeetnest.context import (
    ContextMetadata,
    ContextProvider,
    ContextProviderResult,
    ContextRequest,
    MacroSnapshot,
    MeetingContext,
    UnsupportedContextRequestError,
)


class DeterministicMacroProvider:
    """Test provider that contributes macro context without side effects."""

    provider_name = "deterministic_macro"

    def supports(self, request: ContextRequest) -> bool:
        return request.include_macro and bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        fetched_at = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            macro=MacroSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                observed_on=date(2026, 6, 29),
                indicators=("Rates remain restrictive.",),
                summary="Deterministic macro context for tests.",
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"fixture": "macro"},
        )


def test_provider_declares_whether_it_supports_request() -> None:
    """A provider should advertise support before context assembly."""
    provider: ContextProvider = DeterministicMacroProvider()

    supported = ContextRequest(question="Review AMD.", symbols=("AMD",))
    unsupported = ContextRequest(
        question="Review AMD without macro.",
        symbols=("AMD",),
        include_macro=False,
    )

    assert provider.supports(supported) is True
    assert provider.supports(unsupported) is False


def test_provider_returns_deterministic_context_contribution() -> None:
    """A provider should return only its partial context contribution."""
    provider: ContextProvider = DeterministicMacroProvider()
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = provider.build_context(request)

    assert result.ok is True
    assert result.partial_context.request == request
    assert result.partial_context.macro is not None
    assert result.partial_context.macro.source == "deterministic_macro"
    assert result.partial_context.macro.indicators == ("Rates remain restrictive.",)
    assert result.partial_context.market is None
    assert result.partial_context.news is None
    assert result.partial_context.portfolio is None


def test_provider_result_includes_name_and_metadata() -> None:
    """Provider results should preserve provider identity and metadata."""
    provider: ContextProvider = DeterministicMacroProvider()
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = provider.build_context(request)

    assert result.provider_name == "deterministic_macro"
    assert result.partial_context.metadata.sources == ("deterministic_macro",)
    assert result.metadata == {"fixture": "macro"}
    assert result.warnings == ()
    assert result.errors == ()


def test_unsupported_provider_behavior_is_clear() -> None:
    """Unsupported requests should fail with a domain-specific error."""
    provider: ContextProvider = DeterministicMacroProvider()
    request = ContextRequest(
        question="Review AMD without macro.",
        symbols=("AMD",),
        include_macro=False,
    )

    with pytest.raises(UnsupportedContextRequestError) as exc_info:
        provider.build_context(request)

    assert exc_info.value.provider_name == "deterministic_macro"
    assert exc_info.value.request == request
    assert "does not support request" in str(exc_info.value)
