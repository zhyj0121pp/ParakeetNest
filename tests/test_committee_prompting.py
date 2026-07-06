"""Tests for persona-driven committee prompt generation."""

from __future__ import annotations

from parakeetnest.committee import (
    ADVISORY_ONLY_DISCLAIMER,
    CommitteeOpinionStyle,
    CommitteePersona,
    CommitteePromptContext,
    CommitteeRole,
    PERMANENT_COMMITTEE_PERSONAS,
    PersonaDrivenCommitteePromptBuilder,
    PersonaDrivenPositionReviewPromptBuilder,
)
from parakeetnest.decision import PositionContext


def test_prompt_builder_creates_three_prompts_in_daily_committee_order() -> None:
    prompts = PersonaDrivenCommitteePromptBuilder().build_prompts(
        _default_contexts(),
    )

    assert [prompt.persona_id for prompt in prompts] == [
        "dongdong",
        "xixi",
        "youyou",
    ]


def test_each_prompt_contains_persona_identity_role_and_disclaimer() -> None:
    prompts = PersonaDrivenCommitteePromptBuilder().build_prompts(
        _default_contexts(),
    )

    for prompt in prompts:
        assert prompt.display_name in prompt.prompt_text
        assert prompt.role_title in prompt.prompt_text
        assert prompt.context.persona.responsibility in prompt.prompt_text
        assert ADVISORY_ONLY_DISCLAIMER in prompt.prompt_text


def test_each_prompt_contains_relevant_ticker_report_context() -> None:
    prompts = PersonaDrivenCommitteePromptBuilder().build_prompts(
        _default_contexts(),
    )

    for prompt in prompts:
        assert "- Tickers: NVDA, AAPL" in prompt.prompt_text
        assert "NVDA: portfolio holding with AI demand catalyst." in prompt.prompt_text
        assert "AAPL: watchlist item with services-margin thesis." in prompt.prompt_text
        assert "NVDA: Export controls." in prompt.prompt_text
        assert "AAPL: Services growth." in prompt.prompt_text


def test_prompt_builder_uses_persona_fields_instead_of_id_branches() -> None:
    custom_persona = CommitteePersona(
        id="dongdong",
        display_name="Custom Dong",
        role=CommitteeRole.CHIEF_GROWTH_OFFICER,
        role_title="Custom Opportunity Lead",
        responsibility="Challenge consensus with custom growth evidence.",
        default_viewpoint="Use the custom upside lens.",
        risk_posture="Curious but bounded.",
        evidence_requirements=("Custom product adoption evidence.",),
        writing_style=CommitteeOpinionStyle.OPTIMISTIC_EVIDENCE_BASED,
        decision_biases_to_avoid=("Custom narrative bias.",),
    )
    context = _context_for(custom_persona)

    prompt = PersonaDrivenCommitteePromptBuilder().build_prompt(context)

    assert "Custom Dong" in prompt.prompt_text
    assert "Custom Opportunity Lead" in prompt.prompt_text
    assert "Challenge consensus with custom growth evidence." in prompt.prompt_text
    assert "Use the custom upside lens." in prompt.prompt_text
    assert "Custom product adoption evidence." in prompt.prompt_text
    assert "Custom narrative bias." in prompt.prompt_text


def test_prompts_do_not_introduce_trading_execution_instructions() -> None:
    prompts = PersonaDrivenCommitteePromptBuilder().build_prompts(
        _default_contexts(),
    )
    combined = "\n".join(prompt.prompt_text.lower() for prompt in prompts)

    forbidden_phrases = (
        "execute a trade",
        "place a buy order",
        "place a sell order",
        "route an order",
        "connect to a broker api",
    )
    assert all(phrase not in combined for phrase in forbidden_phrases)


def test_position_review_prompts_include_symbol_and_company_name() -> None:
    prompts = PersonaDrivenPositionReviewPromptBuilder().build_prompts(
        _position_context(),
    )

    for prompt in prompts:
        assert "- Symbol: NVDA" in prompt.prompt_text
        assert "- Company name: NVIDIA Corporation" in prompt.prompt_text


def test_position_review_prompts_preserve_role_specific_perspectives() -> None:
    prompts = {
        prompt.persona_id: prompt.prompt_text.lower()
        for prompt in PersonaDrivenPositionReviewPromptBuilder().build_prompts(
            _position_context(),
        )
    }

    assert "opportunity" in prompts["dongdong"]
    assert "growth" in prompts["dongdong"]
    assert "upside" in prompts["dongdong"]
    assert "catalysts" in prompts["dongdong"]

    assert "fundamentals" in prompts["xixi"]
    assert "valuation" in prompts["xixi"]
    assert "business quality" in prompts["xixi"]

    assert "risk" in prompts["youyou"]
    assert "downside" in prompts["youyou"]
    assert "concentration" in prompts["youyou"]
    assert "uncertainty" in prompts["youyou"]


def test_position_review_prompt_output_schema_mentions_review_fields() -> None:
    prompts = PersonaDrivenPositionReviewPromptBuilder().build_prompts(
        _position_context(),
    )
    required_fields = (
        "symbol",
        "agent_name",
        "thesis",
        "concerns",
        "recommendation",
        "confidence",
        "evidence_refs",
    )

    for prompt in prompts:
        assert "CommitteePositionReview" in prompt.prompt_text
        for field in required_fields:
            assert field in prompt.prompt_text


def test_position_review_prompts_are_provider_neutral() -> None:
    prompts = PersonaDrivenPositionReviewPromptBuilder().build_prompts(
        _position_context(),
    )
    combined = "\n".join(prompt.prompt_text.lower() for prompt in prompts)

    provider_terms = (
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "robinhood",
        "yahoo",
        "gmail",
    )
    assert all(term not in combined for term in provider_terms)


def _default_contexts() -> tuple[CommitteePromptContext, ...]:
    return tuple(_context_for(persona) for persona in PERMANENT_COMMITTEE_PERSONAS)


def _context_for(persona: CommitteePersona) -> CommitteePromptContext:
    return CommitteePromptContext(
        persona=persona,
        tickers=("NVDA", "AAPL"),
        market_summary="Market context covers requested tickers.",
        portfolio_review="Portfolio review found 1 covered holding.",
        watchlist_review="Watchlist review found 1 covered item.",
        ticker_summaries=(
            "NVDA: portfolio holding with AI demand catalyst.",
            "AAPL: watchlist item with services-margin thesis.",
        ),
        evidence_notes=("Research assembled from provider-neutral services.",),
        key_risks=("NVDA: Export controls.", "AAPL: China demand risk."),
        upcoming_catalysts=("NVDA: Datacenter demand.", "AAPL: Services growth."),
    )


def _position_context() -> PositionContext:
    return PositionContext(
        symbol="NVDA",
        company_name="NVIDIA Corporation",
        quantity=2,
        market_value=1840,
        portfolio_weight=0.25,
        cost_basis=820,
        unrealized_gain_loss=200,
        current_price=920,
        recent_price_change=0.03,
        relevant_news=("Blackwell demand remains strong.",),
        relevant_research=("Prior thesis favors durable AI infrastructure demand.",),
        risk_notes=("Position is a large portfolio weight.",),
        valuation_notes=("Premium multiple requires durable earnings growth.",),
        momentum_notes=("Trend remains positive.",),
        portfolio_notes=("Largest current holding.",),
    )
