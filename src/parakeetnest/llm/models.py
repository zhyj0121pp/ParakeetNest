"""Provider-independent LLM request and response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


JSONSchema = dict[str, Any]


@dataclass(frozen=True)
class LLMRequest:
    """A normalized model request with no provider-specific fields."""

    prompt: str
    model: str
    system_prompt: str | None = None
    temperature: float = 0.0
    response_schema: JSONSchema | None = None
    timeout_seconds: float | None = None
    max_retries: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMError:
    """Provider-independent error details for model calls."""

    code: str
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class LLMResponse:
    """A normalized model response for committee and report parsing."""

    content: str
    model: str
    provider_name: str
    finish_reason: Literal["stop", "length", "timeout", "error"] = "stop"
    error: LLMError | None = None
    retry_count: int = 0
    latency_ms: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Return whether the response completed without provider error."""
        return self.error is None and self.finish_reason not in {"timeout", "error"}
