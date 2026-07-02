"""Tests for the provider-independent LLM abstraction layer."""

from __future__ import annotations

import json

import pytest

from parakeetnest.committee.models import InvestmentContext
from parakeetnest.config import LLMConfig
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.llm import (
    CHAIRMAN_SUMMARY_SCHEMA,
    COMMITTEE_OPINION_SCHEMA,
    DAILY_REPORT_SCHEMA,
    LLMProvider,
    LLMRequest,
    MockLLMProvider,
    OpenAIProvider,
    OutputParser,
    OutputParserError,
    PromptContextBuilder,
    create_llm_provider_registry,
)
from parakeetnest.llm.prompts import TextPromptBuilder
from parakeetnest.models import ConfidenceLevel, RecommendationAction


def test_mock_llm_provider_implements_provider_protocol_without_network() -> None:
    """The fake provider should satisfy the protocol and record requests."""
    provider: LLMProvider = MockLLMProvider(
        responses=(json.dumps({"member_name": "Xixi"}),)
    )
    request = LLMRequest(prompt="Return JSON.", model="mock-committee")

    response = provider.complete(request)

    assert response.ok is True
    assert response.provider_name == "mock"
    assert json.loads(response.content) == {"member_name": "Xixi"}
    assert isinstance(provider, MockLLMProvider)
    assert provider.requests == [request]


def test_openai_provider_constructs_chat_completion_request_with_fake_client() -> None:
    """The OpenAI provider should translate neutral requests at the provider edge."""
    client = _FakeOpenAIClient(
        {
            "choices": [
                {
                    "message": {"content": json.dumps({"action": "watch"})},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }
    )
    provider = OpenAIProvider(client=client, default_model="gpt-test")
    request = LLMRequest(
        prompt="Return JSON.",
        model="gpt-override",
        system_prompt="You are ParakeetNest.",
        temperature=0.2,
        response_schema={"type": "object", "required": ["action"]},
        timeout_seconds=12.5,
    )

    response = provider.complete(request)

    assert response.ok is True
    assert response.provider_name == "openai"
    assert response.model == "gpt-override"
    assert json.loads(response.content) == {"action": "watch"}
    assert response.metadata["total_tokens"] == "15"
    assert client.kwargs == {
        "model": "gpt-override",
        "messages": [
            {"role": "system", "content": "You are ParakeetNest."},
            {"role": "user", "content": "Return JSON."},
        ],
        "temperature": 0.2,
        "timeout": 12.5,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "parakeetnest_response",
                "schema": {"type": "object", "required": ["action"]},
                "strict": True,
            },
        },
    }


def test_openai_provider_requires_api_key_without_injected_client() -> None:
    """OpenAI should fail configuration early when no API key is supplied."""
    with pytest.raises(ConfigurationError, match="requires an API key"):
        OpenAIProvider(api_key=None)


def test_openai_provider_normalizes_malformed_response_from_fake_client() -> None:
    """Malformed OpenAI responses should not leak raw exceptions."""
    provider = OpenAIProvider(
        client=_FakeOpenAIClient({"choices": []}),
        default_model="gpt-test",
    )

    response = provider.complete(LLMRequest(prompt="Return JSON.", model="gpt-test"))

    assert response.ok is False
    assert response.finish_reason == "error"
    assert response.error is not None
    assert response.provider_name == "openai"


def test_llm_provider_registry_selects_mock_provider() -> None:
    """Provider selection should be registry-based and keep mock available."""
    registry = create_llm_provider_registry()

    provider = registry.resolve(LLMConfig(provider="mock", model="unit-model"))

    assert isinstance(provider, MockLLMProvider)
    response = provider.complete(LLMRequest(prompt="x", model=""))
    assert response.model == "unit-model"


def test_llm_provider_registry_mock_is_default() -> None:
    """The default LLM provider should remain the deterministic mock."""
    provider = create_llm_provider_registry().default()

    assert isinstance(provider, MockLLMProvider)


def test_prompt_context_builder_preserves_memory_before_current_facts() -> None:
    """Prompts should put thesis and discussion memory before fresh facts."""
    investment_context = InvestmentContext(
        symbol="NVDA",
        historical_thesis=("Prior AI thesis.",),
        historical_discussions=("Prior valuation discussion.",),
        current_facts=("Fresh margin fact.",),
    )
    context = PromptContextBuilder().build(
        "committee_opinion",
        investment_context,
        output_schema=COMMITTEE_OPINION_SCHEMA,
    )

    request = TextPromptBuilder(model="mock").build(context)

    assert request.response_schema is COMMITTEE_OPINION_SCHEMA
    assert request.prompt.index("Prior AI thesis.") < request.prompt.index("Fresh margin fact.")
    assert "Return only output" in (request.system_prompt or "")


def test_output_parser_parses_committee_opinion() -> None:
    """Valid model JSON should become the typed committee dataclass."""
    response = MockLLMProvider(
        responses=(
            json.dumps(
                {
                    "member_name": "Yoyo",
                    "role": "Chief Risk Officer",
                    "symbol": "AMD",
                    "viewpoint": "Risk remains manageable but valuation must be watched.",
                    "confidence": "medium",
                    "evidence": [
                        {"summary": "Balance sheet is resilient.", "source": "mock_fixture"}
                    ],
                    "risks": ["Multiple compression."],
                    "catalysts": ["Product cycle update."],
                }
            ),
        )
    ).complete(LLMRequest(prompt="x", model="mock"))

    opinion = OutputParser().parse_committee_opinion(response)

    assert opinion.member_name == "Yoyo"
    assert opinion.confidence is ConfidenceLevel.MEDIUM
    assert opinion.evidence[0].source == "mock_fixture"


def test_output_parser_parses_chairman_summary_with_required_recommendation_fields() -> None:
    """Chairman JSON must include action, confidence, horizon, evidence, risks, and catalysts."""
    response = MockLLMProvider(
        responses=(
            json.dumps(
                {
                    "symbol": "MSFT",
                    "action": "watch",
                    "confidence": "low",
                    "horizon": "3_months",
                    "rationale": "Wait for more validated evidence.",
                    "evidence": [
                        {"summary": "Cloud growth was cited.", "source": "mock_fixture"}
                    ],
                    "risks": ["Execution risk."],
                    "catalysts": ["Earnings update."],
                    "data_confidence": "low",
                }
            ),
        )
    ).complete(LLMRequest(prompt="x", model="mock"))

    summary = OutputParser().parse_chairman_summary(response)

    assert summary.action is RecommendationAction.WATCH
    assert summary.risks == ("Execution risk.",)


def test_output_parser_fails_closed_for_missing_required_fields() -> None:
    """Invalid structured output should not reach committee decision logic."""
    response = MockLLMProvider(
        responses=(
            json.dumps(
                {
                    "symbol": "MSFT",
                    "action": "watch",
                    "confidence": "low",
                }
            ),
        )
    ).complete(LLMRequest(prompt="x", model="mock"))

    with pytest.raises(OutputParserError, match="missing required fields"):
        OutputParser().parse_chairman_summary(response)


def test_daily_report_schema_validates_report_shape() -> None:
    """The daily report schema should validate nested committee outputs."""
    chairman_summary = {
        "symbol": "NVDA",
        "action": "watch",
        "confidence": "medium",
        "horizon": "3_months",
        "rationale": "Watch for confirmation.",
        "evidence": [{"summary": "Validated growth.", "source": "mock_fixture"}],
        "risks": ["Valuation risk."],
        "catalysts": ["Earnings."],
        "data_confidence": "medium",
    }
    committee_opinion = {
        "member_name": "Dongdong",
        "role": "Chief Opportunity Hunter",
        "symbol": "NVDA",
        "viewpoint": "There are visible catalysts.",
        "confidence": "medium",
        "evidence": [{"summary": "AI demand.", "source": "mock_fixture"}],
        "risks": [],
        "catalysts": ["Product launch."],
    }
    response = MockLLMProvider(
        responses=(
            json.dumps(
                {
                    "report_date": "2026-06-29",
                    "portfolio_summary": "Portfolio is watchful.",
                    "market_summary": "Market breadth is mixed.",
                    "committee_opinions": [committee_opinion],
                    "chairman_summary": chairman_summary,
                    "recommendations": [chairman_summary],
                    "risks": ["Valuation risk."],
                    "catalysts": ["Earnings."],
                }
            ),
        )
    ).complete(LLMRequest(prompt="x", model="mock"))

    report = OutputParser().parse_daily_report(response)

    assert report["chairman_summary"]["symbol"] == "NVDA"
    assert report["recommendations"][0]["action"] == "watch"
    assert DAILY_REPORT_SCHEMA["required"]
    assert CHAIRMAN_SUMMARY_SCHEMA["required"]


class _FakeOpenAIClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.kwargs: dict | None = None
        self.chat = self
        self.completions = self

    def create(self, **kwargs: object) -> dict:
        self.kwargs = kwargs
        return self.response
