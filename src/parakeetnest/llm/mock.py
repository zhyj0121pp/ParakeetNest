"""Deterministic LLM provider for tests."""

from __future__ import annotations

import json
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
        """Return the next queued response or a deterministic schema-valid response."""
        self.requests.append(request)
        if not self._responses:
            return LLMResponse(
                content=self._default_response(request),
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

    @staticmethod
    def _default_response(request: LLMRequest) -> str:
        response_schema = request.response_schema or {}
        required = set(response_schema.get("required", ()))
        evidence = [
            {
                "summary": "Deterministic mock response.",
                "source": "MockLLMProvider",
                "observed_at": None,
            }
        ]
        if "portfolio_view" in required:
            return json.dumps(
                {
                    "agent_name": request.metadata.get("agent_name", "Mock Agent"),
                    "role": request.metadata.get("role", "Portfolio Committee Member"),
                    "portfolio_view": (
                        "Mock portfolio committee observation generated for local "
                        "development."
                    ),
                    "advisory_action": "monitor",
                    "confidence": "medium",
                    "horizon": "3_months",
                    "evidence": evidence,
                    "risks": ["Mock output is advisory research only."],
                    "catalysts": ["Replace mock inputs with richer research context later."],
                },
                sort_keys=True,
            )
        if "rationale" in required:
            return json.dumps(
                {
                    "symbol": "UNKNOWN",
                    "action": "watch",
                    "confidence": "medium",
                    "horizon": "3_months",
                    "rationale": "Mock committee recommends watching while gathering real data.",
                    "evidence": evidence,
                    "risks": ["No real market data, news, or filings were used."],
                    "catalysts": ["Connect real research inputs in a future epic."],
                    "data_confidence": "medium",
                },
                sort_keys=True,
            )
        return json.dumps(
            {
                "member_name": request.metadata.get("agent_name", "Mock Agent"),
                "role": request.metadata.get("role", "Committee Member"),
                "symbol": "UNKNOWN",
                "viewpoint": "Mock response generated for local and test execution.",
                "confidence": "medium",
                "evidence": evidence,
                "risks": ["Mock output is not investment advice."],
                "catalysts": ["Replace mock provider with real research inputs later."],
            },
            sort_keys=True,
        )
