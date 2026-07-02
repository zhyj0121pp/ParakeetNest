"""OpenAI LLM provider implementation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from parakeetnest.exceptions import ConfigurationError
from parakeetnest.llm.models import LLMError, LLMRequest, LLMResponse
from parakeetnest.llm.provider import LLMProvider


@dataclass
class OpenAIProvider(LLMProvider):
    """OpenAI-backed provider behind the provider-neutral LLM interface."""

    api_key: str | None = None
    client: Any | None = None
    default_model: str = "gpt-4.1-mini"
    name: str = "openai"

    def __post_init__(self) -> None:
        if self.client is not None:
            return
        if self.api_key is None or not self.api_key.strip():
            raise ConfigurationError(
                "OpenAI LLM provider requires an API key from the configured "
                "environment variable."
            )
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ConfigurationError(
                "OpenAI LLM provider requires the optional 'openai' package."
            ) from error
        self.client = OpenAI(api_key=self.api_key)

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a normalized response from OpenAI Chat Completions."""
        started_at = perf_counter()
        model = request.model or self.default_model
        try:
            response = self.client.chat.completions.create(
                **self._build_request_kwargs(request, model=model)
            )
            choice = self._first_choice(response)
            content = self._message_content(choice)
            finish_reason = self._finish_reason(choice)
            return LLMResponse(
                content=content,
                model=model,
                provider_name=self.name,
                finish_reason=finish_reason,
                latency_ms=self._elapsed_ms(started_at),
                metadata=self._usage_metadata(response),
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures.
            return self._error_response(exc, model=model, started_at=started_at)

    def _build_request_kwargs(self, request: LLMRequest, *, model: str) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.timeout_seconds is not None:
            kwargs["timeout"] = request.timeout_seconds
        if request.response_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "parakeetnest_response",
                    "schema": request.response_schema,
                    "strict": True,
                },
            }
        return kwargs

    @staticmethod
    def _first_choice(response: Any) -> Any:
        choices = _read(response, "choices", [])
        if not choices:
            raise ValueError("OpenAI response did not include choices.")
        return choices[0]

    @staticmethod
    def _message_content(choice: Any) -> str:
        message = _read(choice, "message", {})
        content = _read(message, "content", "")
        if isinstance(content, str):
            return content
        return str(content)

    @staticmethod
    def _finish_reason(choice: Any) -> str:
        finish_reason = _read(choice, "finish_reason", "stop") or "stop"
        if finish_reason in {"stop", "length"}:
            return finish_reason
        return "error"

    @staticmethod
    def _usage_metadata(response: Any) -> dict[str, str]:
        usage = _read(response, "usage", None)
        if usage is None:
            return {}
        metadata: dict[str, str] = {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = _read(usage, key, None)
            if value is not None:
                metadata[key] = str(value)
        return metadata

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)

    def _error_response(
        self,
        exc: Exception,
        *,
        model: str,
        started_at: float,
    ) -> LLMResponse:
        return LLMResponse(
            content="",
            model=model,
            provider_name=self.name,
            finish_reason="error",
            error=LLMError(
                code=exc.__class__.__name__,
                message=str(exc) or exc.__class__.__name__,
                retryable=False,
            ),
            latency_ms=self._elapsed_ms(started_at),
        )


def _read(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


__all__ = ["OpenAIProvider"]
