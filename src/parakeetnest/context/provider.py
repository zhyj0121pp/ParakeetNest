"""Provider abstraction for Context Layer contributions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from parakeetnest.context.models import ContextRequest, MeetingContext
from parakeetnest.exceptions import ParakeetNestError


@dataclass(frozen=True)
class ContextProviderResult:
    """A provider's partial contribution to a future MeetingContext."""

    provider_name: str
    partial_context: MeetingContext
    metadata: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """Return whether the provider completed without errors."""
        return not self.errors


class UnsupportedContextRequestError(ParakeetNestError):
    """Raised when a provider is asked to build unsupported context."""

    def __init__(self, provider_name: str, request: ContextRequest) -> None:
        self.provider_name = provider_name
        self.request = request
        super().__init__(
            f"Context provider '{provider_name}' does not support request: "
            f"{request.question}"
        )


class ContextProvider(Protocol):
    """Provider-independent interface for Context Layer data sources."""

    provider_name: str

    def supports(self, request: ContextRequest) -> bool:
        """Return whether this provider can contribute to the request."""

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        """Return a deterministic partial context contribution."""
