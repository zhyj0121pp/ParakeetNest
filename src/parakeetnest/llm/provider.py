"""Provider protocol for language-model calls."""

from __future__ import annotations

from typing import Protocol

from parakeetnest.llm.models import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    """Provider-independent interface implemented by all LLM backends."""

    name: str

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a model response without exposing provider-specific details."""
