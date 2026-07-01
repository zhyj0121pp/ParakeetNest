"""Tests for committee agent runtime domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from parakeetnest.committee.agent_runtime import (
    AgentExecutionMetadata,
    AgentExecutionResult,
    AgentRequest,
    AgentResponse,
)


def _request() -> AgentRequest:
    return AgentRequest(
        request_id="turn-1",
        agent_id="xixi",
        prompt="Evaluate NVDA fundamentals.",
        output_schema_id="committee_opinion",
        metadata={"meeting_id": "42"},
    )


def _response() -> AgentResponse:
    return AgentResponse(
        agent_id="xixi",
        content='{"viewpoint": "Constructive."}',
        output_schema_id="committee_opinion",
        parsed_payload={
            "viewpoint": "Constructive.",
            "evidence": [{"summary": "Revenue growth.", "source": "unit_test"}],
        },
        metadata={"finish_reason": "stop"},
    )


def _metadata() -> AgentExecutionMetadata:
    return AgentExecutionMetadata(
        execution_id="exec-1",
        agent_id="xixi",
        model="mock-committee",
        provider_name="mock",
        started_at=datetime(2026, 6, 30, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 6, 30, 12, 0, 1, tzinfo=UTC),
        latency_ms=1000,
        retry_count=1,
        finish_reason="stop",
        metadata={"trace_id": "trace-1"},
    )


def test_agent_runtime_models_create_normalized_immutable_values() -> None:
    request = AgentRequest(
        request_id=" turn-1 ",
        agent_id=" xixi ",
        prompt=" Evaluate NVDA fundamentals. ",
        output_schema_id=" committee_opinion ",
        metadata={" meeting_id ": " 42 "},
    )
    response = _response()
    result = AgentExecutionResult(
        request=request,
        metadata=_metadata(),
        response=response,
    )

    assert request.request_id == "turn-1"
    assert request.agent_id == "xixi"
    assert request.prompt == "Evaluate NVDA fundamentals."
    assert request.metadata["meeting_id"] == "42"
    assert response.parsed_payload is not None
    assert response.parsed_payload["evidence"] == (
        {"summary": "Revenue growth.", "source": "unit_test"},
    )
    assert result.response is response

    with pytest.raises(FrozenInstanceError):
        request.prompt = "Changed"
    with pytest.raises(TypeError):
        request.metadata["meeting_id"] = "43"
    with pytest.raises(TypeError):
        response.parsed_payload["viewpoint"] = "Changed"  # type: ignore[index]


def test_agent_runtime_models_validate_required_fields_and_consistency() -> None:
    with pytest.raises(ValueError, match="agent_id must be lowercase snake_case"):
        AgentRequest(
            request_id="turn-1",
            agent_id="Bad Agent",
            prompt="Prompt.",
            output_schema_id="committee_opinion",
        )

    with pytest.raises(ValueError, match="prompt is required"):
        AgentRequest(
            request_id="turn-1",
            agent_id="xixi",
            prompt=" ",
            output_schema_id="committee_opinion",
        )

    with pytest.raises(ValueError, match="latency_ms must be non-negative"):
        AgentExecutionMetadata(
            execution_id="exec-1",
            agent_id="xixi",
            model="mock",
            provider_name="mock",
            latency_ms=-1,
        )

    with pytest.raises(ValueError, match="request and metadata agent_id must match"):
        AgentExecutionResult(
            request=_request(),
            metadata=AgentExecutionMetadata(
                execution_id="exec-1",
                agent_id="yoyo",
                model="mock",
                provider_name="mock",
            ),
            response=_response(),
        )

    with pytest.raises(ValueError, match="either response or error_message"):
        AgentExecutionResult(request=_request(), metadata=_metadata())


def test_agent_execution_result_can_capture_failure_without_response() -> None:
    result = AgentExecutionResult(
        request=_request(),
        metadata=_metadata(),
        error_message="Provider timeout.",
    )

    assert result.response is None
    assert result.error_message == "Provider timeout."


def test_agent_runtime_models_compare_by_value() -> None:
    assert _request() == _request()
    assert _response() == _response()
    assert _metadata() == _metadata()
    assert AgentExecutionResult(
        request=_request(),
        metadata=_metadata(),
        response=_response(),
    ) == AgentExecutionResult(
        request=_request(),
        metadata=_metadata(),
        response=_response(),
    )

    assert _request() != AgentRequest(
        request_id="turn-2",
        agent_id="xixi",
        prompt="Evaluate NVDA fundamentals.",
        output_schema_id="committee_opinion",
    )


def test_agent_runtime_models_serialize_round_trip() -> None:
    result = AgentExecutionResult(
        request=_request(),
        metadata=_metadata(),
        response=_response(),
    )

    payload = result.to_dict()
    restored = AgentExecutionResult.from_dict(payload)

    assert restored == result
    assert payload["metadata"]["started_at"] == "2026-06-30T12:00:00+00:00"
    assert payload["response"]["parsed_payload"]["evidence"] == [
        {"summary": "Revenue growth.", "source": "unit_test"},
    ]
