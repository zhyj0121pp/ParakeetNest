"""Service for assembling complete committee meeting context."""

from __future__ import annotations

from collections.abc import Iterable

from parakeetnest.context.models import ContextMetadata, ContextRequest, MeetingContext
from parakeetnest.context.provider import ContextProvider


_CONTEXT_SECTIONS = (
    "market",
    "news",
    "filings",
    "portfolio",
    "macro",
    "knowledge_base",
)


class ContextService:
    """Coordinate context providers into one deterministic MeetingContext."""

    def __init__(self, providers: Iterable[ContextProvider]) -> None:
        self._providers = tuple(providers)

    def build_context(self, request: ContextRequest) -> MeetingContext:
        """Build a complete meeting context from supported providers."""
        sections = dict.fromkeys(_CONTEXT_SECTIONS)
        generated_at = request.as_of
        sources: list[str] = []
        warnings: list[str] = []
        data_quality_notes: list[str] = []

        for provider in self._providers:
            if not provider.supports(request):
                continue

            result = provider.build_context(request)
            provider_name = result.provider_name
            partial_context = result.partial_context
            partial_metadata = partial_context.metadata

            if generated_at is None:
                generated_at = partial_metadata.generated_at

            sources.extend(partial_metadata.sources)
            warnings.extend(partial_metadata.warnings)
            warnings.extend(result.warnings)
            data_quality_notes.extend(partial_metadata.data_quality_notes)
            data_quality_notes.extend(
                self._provider_metadata_notes(provider_name, result.metadata)
            )

            for error in result.errors:
                warnings.append(f"{provider_name} error: {error}")

            for section in _CONTEXT_SECTIONS:
                contribution = getattr(partial_context, section)
                if contribution is None:
                    continue

                if sections[section] is None:
                    sections[section] = contribution
                    continue

                warnings.append(
                    f"{provider_name} skipped {section}: section already populated"
                )

        return MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=generated_at,
                sources=tuple(sources),
                data_quality_notes=tuple(data_quality_notes),
                warnings=tuple(warnings),
            ),
            **sections,
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
