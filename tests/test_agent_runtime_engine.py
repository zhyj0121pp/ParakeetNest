"""Tests for the ADR-004 committee agent runtime engine."""

from __future__ import annotations

from dataclasses import dataclass

from parakeetnest.committee.agent_runtime import (
    AgentRequest,
    AgentRuntime,
    DefaultAgentRuntime,
)
from parakeetnest.llm import LLMError, LLMRequest, LLMResponse, MockLLMProvider


def _request() -> AgentRequest:
    return AgentRequest(
        request_id="turn-1",
        agent_id="xixi",
        prompt="Evaluate NVDA fundamentals.",
        output_schema_id="committee_opinion",
        metadata={"trace_id": "trace-1"},
    )


def test_default_agent_runtime_executes_single_request_with_raw_content() -> None:
    provider = MockLLMProvider(
        responses=(
            LLMResponse(
                content='  {"viewpoint": "Constructive."}\n',
                model="unit-model",
                provider_name="mock",
                finish_reason="stop",
                retry_count=1,
                latency_ms=12,
                metadata={"provider_trace_id": "abc"},
            ),
        )
    )
    runtime: AgentRuntime = DefaultAgentRuntime(
        llm_provider=provider,
        model="unit-model",
        temperature=0.2,
        timeout_seconds=3.0,
        max_retries=2,
    )

    result = runtime.execute(_request())

    assert result.error_message is None
    assert result.response is not None
    assert result.response.content == '  {"viewpoint": "Constructive."}\n'
    assert result.response.parsed_payload is None
    assert result.response.output_schema_id == "committee_opinion"
    assert result.response.metadata["provider_trace_id"] == "abc"
    assert result.metadata.agent_id == "xixi"
    assert result.metadata.model == "unit-model"
    assert result.metadata.provider_name == "mock"
    assert result.metadata.finish_reason == "stop"
    assert result.metadata.retry_count == 1
    assert result.metadata.latency_ms == 12
    assert result.metadata.started_at is not None
    assert result.metadata.completed_at is not None
    assert len(provider.requests) == 1
    assert provider.requests[0] == LLMRequest(
        prompt="Evaluate NVDA fundamentals.",
        model="unit-model",
        temperature=0.2,
        timeout_seconds=3.0,
        max_retries=2,
        metadata={
            "trace_id": "trace-1",
            "request_id": "turn-1",
            "agent_id": "xixi",
            "output_schema_id": "committee_opinion",
        },
    )


def test_default_agent_runtime_turns_provider_error_response_into_result_error() -> None:
    provider = MockLLMProvider(
        responses=(
            LLMResponse(
                content="",
                model="unit-model",
                provider_name="mock",
                finish_reason="timeout",
                error=LLMError(
                    code="timeout",
                    message="Provider timed out.",
                    retryable=True,
                ),
                retry_count=2,
                latency_ms=3000,
            ),
        )
    )
    runtime = DefaultAgentRuntime(llm_provider=provider, model="unit-model")

    result = runtime.execute(_request())

    assert result.response is None
    assert result.error_message == "Provider timed out."
    assert result.metadata.finish_reason == "timeout"
    assert result.metadata.retry_count == 2
    assert result.metadata.latency_ms == 3000


def test_default_agent_runtime_turns_provider_exception_into_result_error() -> None:
    @dataclass
    class FailingProvider:
        name: str = "failing"

        def complete(self, request: LLMRequest) -> LLMResponse:
            raise RuntimeError("provider unavailable")

    runtime = DefaultAgentRuntime(llm_provider=FailingProvider(), model="unit-model")

    result = runtime.execute(_request())

    assert result.response is None
    assert result.error_message == "provider unavailable"
    assert result.metadata.model == "unit-model"
    assert result.metadata.provider_name == "failing"
    assert result.metadata.finish_reason == "error"


def test_default_agent_runtime_turns_blank_success_content_into_result_error() -> None:
    provider = MockLLMProvider(
        responses=(
            LLMResponse(
                content=" ",
                model="unit-model",
                provider_name="mock",
            ),
        )
    )
    runtime = DefaultAgentRuntime(llm_provider=provider, model="unit-model")

    result = runtime.execute(_request())

    assert result.response is None
    assert result.error_message == "content is required"
