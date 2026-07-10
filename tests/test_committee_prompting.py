"""Tests for persona-driven committee prompt generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from parakeetnest.committee import (
    ADVISORY_ONLY_DISCLAIMER,
    CommitteeOpinionStyle,
    CommitteePersona,
    CommitteePromptContext,
    CommitteeRole,
    MissingCommitteePlaybookError,
    PERMANENT_COMMITTEE_PERSONAS,
    PersonaDrivenCommitteePromptBuilder,
    PersonaDrivenPositionReviewPromptBuilder,
    PlaybookLoader,
)
from parakeetnest.decision import PositionContext
from parakeetnest.portfolio import PortfolioPositionContext, PortfolioSummary


def test_all_committee_playbook_files_exist() -> None:
    playbook_dir = Path("src/parakeetnest/committee/playbooks")

    for filename in ("system.md", "common.md", "dongdong.md", "xixi.md", "youyou.md"):
        assert (playbook_dir / filename).is_file()


def test_playbook_loader_loads_system_common_and_persona_playbooks() -> None:
    loader = PlaybookLoader()

    assert (
        "ParakeetNest is an AI investment advisory platform"
        in loader.load_system_playbook()
    )
    assert "Use only supplied facts" in loader.load_common_playbook()
    assert "growth acceleration" in loader.load_persona_playbook("dongdong")
    assert "forward PE" in loader.load_persona_playbook("xixi")
    assert "position_size_bucket" in loader.load_persona_playbook("youyou")


def test_missing_playbook_raises_clear_error(tmp_path: Path) -> None:
    loader = PlaybookLoader(playbook_dir=tmp_path)

    with pytest.raises(MissingCommitteePlaybookError, match="Missing committee playbook"):
        loader.load_system_playbook()


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


def test_committee_prompt_separates_public_facts_and_bucketed_portfolio_context() -> None:
    context = _context_for(PERMANENT_COMMITTEE_PERSONAS[0])

    prompt = PersonaDrivenCommitteePromptBuilder().build_prompt(context)

    assert "PUBLIC FACTS" in prompt.prompt_text
    assert "Yahoo / market data facts:" in prompt.prompt_text
    assert "Yahoo / news facts:" in prompt.prompt_text
    assert "Financial statement facts:" in prompt.prompt_text
    assert "SEC EDGAR facts:" in prompt.prompt_text
    assert "FRED macro facts:" in prompt.prompt_text
    assert "PRIVATE PORTFOLIO CONTEXT, BUCKETED" in prompt.prompt_text
    assert "Yahoo/market_data: NVDA price=204.12" in prompt.prompt_text
    assert "Yahoo/news: NVDA, title=Nvidia supplier demand expands" in prompt.prompt_text
    assert "Yahoo/financials: NVDA, revenue=130.00B USD" in prompt.prompt_text
    assert "SEC EDGAR: NVDA 10-Q" in prompt.prompt_text
    assert "FRED/macro: Fed Funds 3.5" in prompt.prompt_text
    assert "- Position size bucket: large" in prompt.prompt_text
    assert "- Portfolio rank bucket: largest" in prompt.prompt_text
    assert "- Unrealized return bucket: gain" in prompt.prompt_text
    assert "- Add allowed: False" in prompt.prompt_text

    forbidden = (
        "Quantity",
        "Market value",
        "Cost basis",
        "Average cost",
        "account_id",
        "1234",
        "1840",
        "820",
        "0.25",
    )
    assert all(term not in prompt.prompt_text for term in forbidden)


def test_committee_prompts_include_reusable_playbook_checklists() -> None:
    prompts = {
        prompt.persona_id: prompt.prompt_text
        for prompt in PersonaDrivenCommitteePromptBuilder().build_prompts(
            _default_contexts(),
        )
    }

    assert "growth durability" in prompts["dongdong"]
    assert "portfolio add_allowed constraint" in prompts["dongdong"]

    assert "PE" in prompts["xixi"]
    assert "forward PE" in prompts["xixi"]
    assert "whether valuation is justified by growth" in prompts["xixi"]

    assert "position_size_bucket" in prompts["youyou"]
    assert "trim_candidate" in prompts["youyou"]
    assert "concentration_level" in prompts["youyou"]


def test_generated_prompt_excludes_raw_robinhood_field_names() -> None:
    prompt = PersonaDrivenCommitteePromptBuilder().build_prompt(
        _context_for(PERMANENT_COMMITTEE_PERSONAS[0]),
    )

    forbidden_raw_fields = (
        "shares",
        "market_value",
        "cost_basis",
        "average_cost",
        "exact_weight",
        "account_id",
    )

    assert all(field not in prompt.prompt_text for field in forbidden_raw_fields)


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


def test_committee_prompt_can_request_chinese_report_facing_content() -> None:
    context = _context_for(PERMANENT_COMMITTEE_PERSONAS[0], report_language="zh")

    prompt = PersonaDrivenCommitteePromptBuilder().build_prompt(context)

    assert "请用中文撰写最终报告中面向读者展示的内容" in prompt.prompt_text
    assert "不要翻译股票代码、公司名称、数据源名称或数字" in prompt.prompt_text


def test_position_review_prompt_can_request_chinese_report_facing_content() -> None:
    prompts = PersonaDrivenPositionReviewPromptBuilder(language="zh").build_prompts(
        _position_context(),
    )

    assert all("请用中文撰写 thesis、concerns 和 evidence_refs" in prompt.prompt_text for prompt in prompts)
    assert all("- Symbol: NVDA" in prompt.prompt_text for prompt in prompts)


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


def _context_for(
    persona: CommitteePersona,
    *,
    report_language: str = "en",
) -> CommitteePromptContext:
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
        portfolio_summary=PortfolioSummary(
            number_of_positions=12,
            cash_allocation_bucket="low",
            concentration_level="high",
            largest_position_bucket="large",
            top5_concentration_bucket="high",
            dominant_sector="Technology",
            style_exposure="growth_tilt",
        ),
        position_context=PortfolioPositionContext(
            ticker="NVDA",
            is_holding=True,
            position_size_bucket="large",
            portfolio_rank_bucket="largest",
            unrealized_return_bucket="gain",
            holding_role="core_holding",
            add_allowed=False,
            trim_candidate=True,
        ),
        public_market_facts=("Yahoo/market_data: NVDA price=204.12",),
        financial_facts=("Yahoo/financials: NVDA, revenue=130.00B USD",),
        news_facts=("Yahoo/news: NVDA, title=Nvidia supplier demand expands",),
        company_facts=("SEC EDGAR: NVDA 10-Q",),
        macro_facts=("FRED/macro: Fed Funds 3.5",),
        report_language=report_language,
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
