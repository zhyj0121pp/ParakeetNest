"""Deterministic LLM provider for tests."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field

from parakeetnest.llm.models import LLMError, LLMRequest, LLMResponse
from parakeetnest.llm.provider import LLMProvider


@dataclass
class MockLLMProvider(LLMProvider):
    """A fake provider that never performs network calls."""

    responses: Iterable[str | LLMResponse] = ()
    name: str = "mock"
    default_model: str = "mock-llm"
    requests: list[LLMRequest] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._responses = deque(self.responses)

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return the next queued response or a deterministic empty JSON object."""
        self.requests.append(request)
        if not self._responses:
            return LLMResponse(
                content="{}",
                model=request.model or self.default_model,
                provider_name=self.name,
            )
        response = self._responses.popleft()
        if isinstance(response, LLMResponse):
            return response
        return LLMResponse(
            content=response,
            model=request.model or self.default_model,
            provider_name=self.name,
        )

    def timeout(self, request: LLMRequest) -> LLMResponse:
        """Return a deterministic timeout-shaped response for tests."""
        self.requests.append(request)
        return LLMResponse(
            content="",
            model=request.model or self.default_model,
            provider_name=self.name,
            finish_reason="timeout",
            error=LLMError(
                code="timeout",
                message="Mock provider timed out.",
                retryable=True,
            ),
        )
