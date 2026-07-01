"""Domain models for prepared committee agent runtime turns.

These models describe runtime inputs, outputs, and execution metadata. They do
not render prompts, call LLM providers, parse provider responses, or orchestrate
committee meetings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping


_AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

JSONValue = (
    str
    | int
    | float
    | bool
    | None
    | tuple["JSONValue", ...]
    | Mapping[str, "JSONValue"]
)


@dataclass(frozen=True)
class AgentRequest:
    """Prepared request for one agent turn."""

    request_id: str
    agent_id: str
    prompt: str
    output_schema_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        request_id = self.request_id.strip()
        agent_id = _normalize_agent_id(self.agent_id)
        prompt = self.prompt.strip()
        output_schema_id = self.output_schema_id.strip()

        if not request_id:
            raise ValueError("request_id is required")
        if not prompt:
            raise ValueError("prompt is required")
        if not output_schema_id:
            raise ValueError("output_schema_id is required")

        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "prompt", prompt)
        object.__setattr__(self, "output_schema_id", output_schema_id)
        object.__setattr__(self, "metadata", _freeze_string_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "prompt": self.prompt,
            "output_schema_id": self.output_schema_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentRequest:
        """Build an agent request from serialized data."""
        return cls(
            request_id=str(payload["request_id"]),
            agent_id=str(payload["agent_id"]),
            prompt=str(payload["prompt"]),
            output_schema_id=str(payload["output_schema_id"]),
            metadata=payload.get("metadata", {}),
        )


@dataclass(frozen=True)
class AgentResponse:
    """Structured response produced for one agent turn."""

    agent_id: str
    content: str
    output_schema_id: str
    parsed_payload: Mapping[str, JSONValue] | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        agent_id = _normalize_agent_id(self.agent_id)
        content = self.content.strip()
        output_schema_id = self.output_schema_id.strip()

        if not content:
            raise ValueError("content is required")
        if not output_schema_id:
            raise ValueError("output_schema_id is required")

        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "output_schema_id", output_schema_id)
        object.__setattr__(
            self,
            "parsed_payload",
            None
            if self.parsed_payload is None
            else _freeze_json_mapping(self.parsed_payload),
        )
        object.__setattr__(self, "metadata", _freeze_string_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "agent_id": self.agent_id,
            "content": self.content,
            "output_schema_id": self.output_schema_id,
            "parsed_payload": _thaw_json(self.parsed_payload),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentResponse:
        """Build an agent response from serialized data."""
        return cls(
            agent_id=str(payload["agent_id"]),
            content=str(payload["content"]),
            output_schema_id=str(payload["output_schema_id"]),
            parsed_payload=payload.get("parsed_payload"),
            metadata=payload.get("metadata", {}),
        )


@dataclass(frozen=True)
class AgentExecutionMetadata:
    """Provider-neutral metadata captured around one agent turn."""

    execution_id: str
    agent_id: str
    model: str
    provider_name: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: int | None = None
    retry_count: int = 0
    finish_reason: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        execution_id = self.execution_id.strip()
        agent_id = _normalize_agent_id(self.agent_id)
        model = self.model.strip()
        provider_name = self.provider_name.strip()
        finish_reason = self.finish_reason.strip() if self.finish_reason else None

        if not execution_id:
            raise ValueError("execution_id is required")
        if not model:
            raise ValueError("model is required")
        if not provider_name:
            raise ValueError("provider_name is required")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if finish_reason == "":
            raise ValueError("finish_reason cannot be blank")

        object.__setattr__(self, "execution_id", execution_id)
        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "provider_name", provider_name)
        object.__setattr__(self, "finish_reason", finish_reason)
        object.__setattr__(self, "metadata", _freeze_string_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "model": self.model,
            "provider_name": self.provider_name,
            "started_at": _datetime_to_string(self.started_at),
            "completed_at": _datetime_to_string(self.completed_at),
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "finish_reason": self.finish_reason,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentExecutionMetadata:
        """Build execution metadata from serialized data."""
        return cls(
            execution_id=str(payload["execution_id"]),
            agent_id=str(payload["agent_id"]),
            model=str(payload["model"]),
            provider_name=str(payload["provider_name"]),
            started_at=_datetime_from_string(payload.get("started_at")),
            completed_at=_datetime_from_string(payload.get("completed_at")),
            latency_ms=payload.get("latency_ms"),
            retry_count=int(payload.get("retry_count", 0)),
            finish_reason=payload.get("finish_reason"),
            metadata=payload.get("metadata", {}),
        )


@dataclass(frozen=True)
class AgentExecutionResult:
    """Persistable result envelope for one prepared agent turn."""

    request: AgentRequest
    metadata: AgentExecutionMetadata
    response: AgentResponse | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.request.agent_id != self.metadata.agent_id:
            raise ValueError("request and metadata agent_id must match")
        if self.response is not None and self.response.agent_id != self.request.agent_id:
            raise ValueError("request and response agent_id must match")
        if self.response is not None and self.error_message is not None:
            raise ValueError("result cannot include both response and error_message")
        if self.response is None and self.error_message is None:
            raise ValueError("result requires either response or error_message")
        if self.error_message is not None:
            error_message = self.error_message.strip()
            if not error_message:
                raise ValueError("error_message cannot be blank")
            object.__setattr__(self, "error_message", error_message)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "request": self.request.to_dict(),
            "metadata": self.metadata.to_dict(),
            "response": None if self.response is None else self.response.to_dict(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentExecutionResult:
        """Build an execution result from serialized data."""
        response_payload = payload.get("response")
        return cls(
            request=AgentRequest.from_dict(payload["request"]),
            metadata=AgentExecutionMetadata.from_dict(payload["metadata"]),
            response=None
            if response_payload is None
            else AgentResponse.from_dict(response_payload),
            error_message=payload.get("error_message"),
        )


def _normalize_agent_id(value: str) -> str:
    agent_id = value.strip()
    if not _AGENT_ID_PATTERN.fullmatch(agent_id):
        raise ValueError("agent_id must be lowercase snake_case")
    return agent_id


def _freeze_string_mapping(values: Mapping[str, str]) -> Mapping[str, str]:
    normalized: dict[str, str] = {}
    for key, value in values.items():
        normalized_key = str(key).strip()
        normalized_value = str(value).strip()
        if not normalized_key:
            raise ValueError("metadata keys cannot be blank")
        if not normalized_value:
            raise ValueError("metadata values cannot be blank")
        normalized[normalized_key] = normalized_value
    return MappingProxyType(normalized)


def _freeze_json_mapping(values: Mapping[str, Any]) -> Mapping[str, JSONValue]:
    normalized: dict[str, JSONValue] = {}
    for key, value in values.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            raise ValueError("parsed_payload keys cannot be blank")
        normalized[normalized_key] = _freeze_json(value)
    return MappingProxyType(normalized)


def _freeze_json(value: Any) -> JSONValue:
    if isinstance(value, Mapping):
        return _freeze_json_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError("parsed_payload must contain only JSON-serializable values")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _datetime_to_string(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _datetime_from_string(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
