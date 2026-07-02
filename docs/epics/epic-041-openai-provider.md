# Epic 041: OpenAI Provider

Status: Completed

## Goal

Add a provider-neutral OpenAI LLM provider while preserving the committee
architecture and keeping the deterministic mock provider as the default.

## Implementation Notes

- `parakeetnest.llm.provider.LLMProvider` remains the provider interface.
- `parakeetnest.llm.mock.MockLLMProvider` remains the default provider for local
  tests and application test wiring.
- `parakeetnest.llm.openai.OpenAIProvider` adapts `LLMRequest` to OpenAI Chat
  Completions and normalizes the result back to `LLMResponse`.
- `parakeetnest.llm.registry.LLMProviderRegistry` resolves configured providers
  by provider ID: `mock` or `openai`.
- Committee domain models and investment judgment logic are unchanged.

## Configuration

`AppConfig` supports a provider-neutral `llm` block:

```python
AppConfig(
    llm={
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "api_key_env_var": "OPENAI_API_KEY",
        "temperature": 0.0,
    }
)
```

The OpenAI API key is read from the configured environment variable at provider
resolution time. No API key value is stored in source control.

The legacy `llm_provider="mock"` initializer path is still accepted and maps to
`llm.provider`.

## Test Boundary

OpenAI tests use an injected fake client. They validate request construction,
missing API key behavior, provider selection, and the mock default without
calling the real OpenAI API.
