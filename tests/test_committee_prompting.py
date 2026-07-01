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
)


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
