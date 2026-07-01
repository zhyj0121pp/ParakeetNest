"""Service for assembling complete committee meeting context."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from parakeetnest.context.models import ContextMetadata, ContextRequest, MeetingContext
from parakeetnest.context.provider import ContextProvider, ContextProviderResult


_CONTEXT_SECTIONS = (
    "market",
    "news",
    "filings",
    "financials",
    "valuation",
    "portfolio",
    "macro",
    "economic_regime",
    "sector_rotation",
    "market_breadth",
    "watchlist",
    "knowledge_base",
)


@dataclass
class _ContextAssembly:
    """Mutable assembly state used while providers contribute context."""

    generated_at: datetime | None
    sections: dict[str, Any] = field(
        default_factory=lambda: dict.fromkeys(_CONTEXT_SECTIONS)
    )
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_quality_notes: list[str] = field(default_factory=list)


class ContextService:
    """Coordinate context providers into one deterministic MeetingContext."""

    def __init__(self, providers: Iterable[ContextProvider]) -> None:
        self._providers = tuple(providers)

    def build_context(self, request: ContextRequest) -> MeetingContext:
        """Build a complete meeting context from supported providers."""
        assembly = _ContextAssembly(generated_at=request.as_of)

        for result in self._supported_provider_results(request):
            self._merge_provider_result(assembly, result)

        return self._build_meeting_context(request, assembly)

    def _supported_provider_results(
        self,
        request: ContextRequest,
    ) -> Iterable[ContextProviderResult]:
        """Execute supported providers in configured order."""
        for provider in self._providers:
            if provider.supports(request):
                yield provider.build_context(request)

    def _merge_provider_result(
        self,
        assembly: _ContextAssembly,
        result: ContextProviderResult,
    ) -> None:
        """Merge one provider result into the in-progress assembly."""
        partial_context = result.partial_context
        partial_metadata = partial_context.metadata

        if assembly.generated_at is None:
            assembly.generated_at = partial_metadata.generated_at

        self._merge_metadata(assembly, result, partial_metadata)
        self._merge_sections(assembly, result)

    def _merge_metadata(
        self,
        assembly: _ContextAssembly,
        result: ContextProviderResult,
        partial_metadata: ContextMetadata,
    ) -> None:
        """Merge provider metadata while preserving deterministic ordering."""
        provider_name = result.provider_name

        assembly.sources.extend(partial_metadata.sources)
        assembly.warnings.extend(partial_metadata.warnings)
        assembly.warnings.extend(result.warnings)
        assembly.data_quality_notes.extend(partial_metadata.data_quality_notes)
        assembly.data_quality_notes.extend(
            self._provider_metadata_notes(provider_name, result.metadata)
        )

        for error in result.errors:
            assembly.warnings.append(f"{provider_name} error: {error}")

    def _merge_sections(
        self,
        assembly: _ContextAssembly,
        result: ContextProviderResult,
    ) -> None:
        """Merge sections with first-provider-wins semantics."""
        partial_context = result.partial_context

        for section in _CONTEXT_SECTIONS:
            contribution = getattr(partial_context, section)
            if contribution is None:
                continue

            if assembly.sections[section] is None:
                assembly.sections[section] = contribution
                continue

            assembly.warnings.append(
                f"{result.provider_name} skipped {section}: section already populated"
            )

    @staticmethod
    def _build_meeting_context(
        request: ContextRequest,
        assembly: _ContextAssembly,
    ) -> MeetingContext:
        """Freeze assembled state into the public MeetingContext model."""
        return MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=assembly.generated_at,
                sources=tuple(assembly.sources),
                data_quality_notes=tuple(assembly.data_quality_notes),
                warnings=tuple(assembly.warnings),
            ),
            **assembly.sections,
        )

    @staticmethod
    def _provider_metadata_notes(
        provider_name: str,
        metadata: dict[str, str],
    ) -> tuple[str, ...]:
        """Represent provider result metadata in ContextMetadata deterministically."""
        if not metadata:
            return ()

        return tuple(
            f"{provider_name}.{key}={value}"
            for key, value in sorted(metadata.items())
        )
