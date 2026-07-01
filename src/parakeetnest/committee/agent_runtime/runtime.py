"""Provider-neutral execution engine for prepared committee agent turns."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from parakeetnest.committee.agent_runtime.models import (
    AgentExecutionMetadata,
    AgentExecutionResult,
    AgentRequest,
    AgentResponse,
)
from parakeetnest.llm.models import LLMRequest, LLMResponse
from parakeetnest.llm.provider import LLMProvider


class AgentRuntime(Protocol):
    """Execute one prepared agent request through a provider-neutral backend."""

    def execute(self, request: AgentRequest) -> AgentExecutionResult:
        """Return a successful or failed execution result for one agent request."""


@dataclass(frozen=True)
class DefaultAgentRuntime:
    """Default runtime backed by the existing LLM provider abstraction."""

    llm_provider: LLMProvider
    model: str = "mock-committee"
    temperature: float = 0.0
    timeout_seconds: float | None = None
    max_retries: int = 0

    def execute(self, request: AgentRequest) -> AgentExecutionResult:
        """Execute one prepared agent request without parsing model output."""
        execution_id = f"agent-exec-{uuid4()}"
        started_at = datetime.now(UTC)
        provider_name = _provider_name(self.llm_provider)

        try:
            llm_response = self.llm_provider.complete(self._build_llm_request(request))
        except Exception as exc:  # noqa: BLE001 - provider failures are result data.
            completed_at = datetime.now(UTC)
            return AgentExecutionResult(
                request=request,
                metadata=self._metadata(
                    execution_id=execution_id,
                    request=request,
                    started_at=started_at,
                    completed_at=completed_at,
                    model=self.model,
                    provider_name=provider_name,
                    finish_reason="error",
                ),
                error_message=_exception_message(exc),
            )

        completed_at = datetime.now(UTC)
        metadata = self._metadata_from_response(
            execution_id=execution_id,
            request=request,
            response=llm_response,
            started_at=started_at,
            completed_at=completed_at,
        )

        if not llm_response.ok:
            return AgentExecutionResult(
                request=request,
                metadata=metadata,
                error_message=_error_message(llm_response),
            )

        try:
            response = AgentResponse(
                agent_id=request.agent_id,
                content=llm_response.content,
                output_schema_id=request.output_schema_id,
                parsed_payload=None,
                metadata=llm_response.metadata,
            )
        except ValueError as exc:
            return AgentExecutionResult(
                request=request,
                metadata=metadata,
                error_message=str(exc),
            )

        return AgentExecutionResult(
            request=request,
            metadata=metadata,
            response=response,
        )

    def _build_llm_request(self, request: AgentRequest) -> LLMRequest:
        metadata = {
            **dict(request.metadata),
            "request_id": request.request_id,
            "agent_id": request.agent_id,
            "output_schema_id": request.output_schema_id,
        }
        return LLMRequest(
            prompt=request.prompt,
            model=self.model,
            temperature=self.temperature,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            metadata=metadata,
        )

    def _metadata_from_response(
        self,
        *,
        execution_id: str,
        request: AgentRequest,
        response: LLMResponse,
        started_at: datetime,
        completed_at: datetime,
    ) -> AgentExecutionMetadata:
        return self._metadata(
            execution_id=execution_id,
            request=request,
            started_at=started_at,
            completed_at=completed_at,
            model=response.model,
            provider_name=response.provider_name,
            latency_ms=response.latency_ms,
            retry_count=response.retry_count,
            finish_reason=response.finish_reason,
            metadata=response.metadata,
        )

    @staticmethod
    def _metadata(
        *,
        execution_id: str,
        request: AgentRequest,
        started_at: datetime,
        completed_at: datetime,
        model: str,
        provider_name: str,
        latency_ms: int | None = None,
        retry_count: int = 0,
        finish_reason: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AgentExecutionMetadata:
        measured_latency_ms = int((completed_at - started_at).total_seconds() * 1000)
        return AgentExecutionMetadata(
            execution_id=execution_id,
            agent_id=request.agent_id,
            model=model,
            provider_name=provider_name,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms if latency_ms is not None else measured_latency_ms,
            retry_count=retry_count,
            finish_reason=finish_reason,
            metadata=metadata or {},
        )


def _provider_name(provider: LLMProvider) -> str:
    return str(getattr(provider, "name", provider.__class__.__name__))


def _error_message(response: LLMResponse) -> str:
    if response.error is not None:
        return response.error.message
    return f"Provider returned finish_reason={response.finish_reason}"


def _exception_message(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__
