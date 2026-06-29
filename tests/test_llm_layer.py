"""Tests for the provider-independent LLM abstraction layer."""

from __future__ import annotations

import json

import pytest

from parakeetnest.committee.models import InvestmentContext
from parakeetnest.llm import (
    CHAIRMAN_SUMMARY_SCHEMA,
    COMMITTEE_OPINION_SCHEMA,
    DAILY_REPORT_SCHEMA,
    LLMProvider,
    LLMRequest,
    MockLLMProvider,
    OutputParser,
    OutputParserError,
    PromptContextBuilder,
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
