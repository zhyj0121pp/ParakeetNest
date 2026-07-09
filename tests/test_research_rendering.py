"""Tests for investment research report interactive HTML rendering."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from parakeetnest.context.models import (
    PortfolioAllocationContextItem,
    PortfolioPosition,
    PortfolioSnapshot,
)
from parakeetnest.decision import (
    ConfidenceLevel,
    DecisionUrgency,
    NewOpportunity,
    PortfolioDecisionSummary,
    PositionDecision,
    PositionRecommendation,
)
from parakeetnest.research import (
    InteractiveHtmlInvestmentResearchReportRenderer,
    InvestmentResearchService,
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchCommitteeConsensus,
    ResearchCommitteeOpinion,
    ResearchCommitteePortfolioView,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
    render_investment_research_report_interactive_html,
)
from parakeetnest.config import get_settings


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)
HTML_H2_STYLE = (
    '<h2 style="font-size: 20px; margin: 24px 0 10px; color: #111827;">'
)


def test_interactive_html_renderer_outputs_standalone_html() -> None:
    body = render_investment_research_report_interactive_html(_sample_report())

    assert body == InteractiveHtmlInvestmentResearchReportRenderer().render(
        _sample_report()
    )
    assert body.startswith("<!doctype html>\n<html>\n")
    assert '<meta charset="utf-8">' in body
    assert "<body style=" in body
    assert body.endswith("</html>\n")
    assert "## 1. Action Required" not in body


def test_interactive_html_can_render_english(monkeypatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()

    body = render_investment_research_report_interactive_html(_sample_report())

    assert ">1. Action Required</h2>" in body
    assert ">2. Position Cards</h2>" in body
    assert "<strong>Recommendation:</strong> Trim" in body
    assert "<strong>Confidence:</strong> High" in body
    assert "This report is advisory guidance only." in body
    get_settings.cache_clear()


def test_interactive_html_position_cards_use_per_position_committee_reviews(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    report = InvestmentResearchService().generate_report(
        ("AAPL", "MSFT"),
        generated_at=GENERATED_AT,
    )

    body = render_investment_research_report_interactive_html(report)
    position_cards = _section(
        body,
        f"{HTML_H2_STYLE}2. Position Cards</h2>",
        f"{HTML_H2_STYLE}3. New Opportunities</h2>",
    )
    aapl_card = _section(position_cards, ">AAPL</span>", ">MSFT</span>")
    msft_card = _section(position_cards, ">MSFT</span>", None)

    assert "<strong>Dongdong:</strong>" in aapl_card
    assert "<strong>Xixi:</strong>" in aapl_card
    assert "<strong>Youyou:</strong>" in aapl_card
    assert "AAPL:" in aapl_card
    assert "MSFT" not in aapl_card
    assert "across 2 ticker(s)" not in aapl_card
    assert "<strong>Dongdong:</strong>" in msft_card
    assert "<strong>Xixi:</strong>" in msft_card
    assert "<strong>Youyou:</strong>" in msft_card
    assert "MSFT:" in msft_card
    assert "AAPL" not in msft_card
    assert "across 2 ticker(s)" not in msft_card
    assert "across 2 ticker(s)" in body
    assert body.index("across 2 ticker(s)") > body.index(
        f"{HTML_H2_STYLE}4. Market Overview</h2>"
    )
    get_settings.cache_clear()


def test_interactive_html_uses_env_language(monkeypatch) -> None:
    monkeypatch.setenv("PARAKEET_REPORT_LANGUAGE", "zh")
    get_settings.cache_clear()

    body = render_investment_research_report_interactive_html(_sample_report())

    assert ">1. 需要处理</h2>" in body
    assert "<strong>建议:</strong> 减仓复核" in body
    assert "本报告仅提供投资分析与复核建议" in body
    get_settings.cache_clear()


def test_interactive_html_explicit_language_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("PARAKEET_REPORT_LANGUAGE", "zh")
    get_settings.cache_clear()

    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="en",
    )

    assert ">1. Action Required</h2>" in body
    assert "<strong>Recommendation:</strong> Trim" in body
    assert ">1. 需要处理</h2>" not in body
    get_settings.cache_clear()


def test_interactive_html_invalid_explicit_language_is_clear() -> None:
    try:
        render_investment_research_report_interactive_html(
            _sample_report(),
            language="fr",
        )
    except ValueError as exc:
        assert "report language must be en or zh" in str(exc)
    else:
        raise AssertionError("invalid report language should raise ValueError")


def test_interactive_html_uses_inline_card_layout_and_badges() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )

    assert 'style="' in body
    assert "border-left: 5px solid #f97316" in body
    assert "border-radius: 10px" in body
    assert ">减仓复核</span>" in body
    assert ">信心：高</span>" in body
    assert ">需要人工复核</span>" in body
    assert "<script" not in body.lower()
    assert "<style" not in body.lower()
    assert "<link" not in body.lower()


def test_interactive_html_position_cards_are_collapsed_by_default() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    card = _first_position_card(body)
    opening_tag = card.split(">", 1)[0]
    summary = _position_card_summary(card)

    assert card.startswith("<details")
    assert " open" not in opening_tag
    assert "NVDA" in summary
    assert "减仓复核" in summary
    assert "信心：高" in summary
    assert "需要人工复核" in summary
    assert "Committee recommends reviewing the position." not in summary


def test_interactive_html_stock_cards_keep_critical_fields_visible() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    card = _first_position_card(body)
    summary = _position_card_summary(card)

    assert card.startswith('<details style="background: #ffffff;')
    assert "NVDA" in summary
    assert "减仓复核" in summary
    assert "信心：高" in summary
    assert "需要人工复核" in summary
    assert "紧急程度" not in summary
    assert "<strong>理由:</strong>" not in summary
    assert "<strong>建议:</strong> 减仓复核" in card
    assert card.index("<strong>建议:</strong> 减仓复核") < card.index("事实依据")


def test_interactive_html_uses_chinese_section_titles() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )

    assert ">1. 需要处理</h2>" in body
    assert ">2. 持仓决策卡片</h2>" in body
    assert ">3. 稳定持仓</h2>" not in body
    assert ">3. 新机会</h2>" in body
    assert ">4. 市场概览</h2>" in body
    assert ">5. 原始证据</h2>" in body


def test_interactive_html_uses_chinese_field_labels() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )

    assert "<strong>建议:</strong> 减仓复核" in body
    assert "<strong>信心:</strong> 高" in body
    assert "<strong>紧急程度:</strong> 高" in body
    assert "<strong>理由:</strong> Committee recommends reviewing the position." in body
    assert "<strong>最终共识:</strong>" in body
    assert "<strong>东东:</strong> Opportunity remains attractive." in body
    assert "<strong>西西:</strong> Fundamentals remain strong." in body
    assert "<strong>悠悠:</strong> Sizing risk requires monitoring." in body


def test_interactive_html_localizes_recommendation_confidence_and_urgency() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )

    assert "减仓复核" in body
    assert "继续观察" in body
    assert "信心：高" in body
    assert "信心：中" in body
    assert "紧急程度：高" in body


def test_interactive_html_contains_progressive_details_sections() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )

    assert "<details" in body
    assert "<summary" in body
    assert "事实依据" in body
    assert "展开稳定持仓" not in body
    assert "展开原始证据" in body


def test_interactive_html_critical_fields_are_visible_outside_details() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    visible_body = _position_card_summary(_first_position_card(body))

    assert "NVDA" in visible_body
    assert "减仓复核" in visible_body
    assert "信心：高" in visible_body
    assert "需要人工复核" in visible_body
    assert "<strong>建议:</strong> 减仓复核" not in visible_body
    assert "<strong>东东:</strong> Opportunity remains attractive." not in visible_body
    assert "Committee reviewed supplied context." not in visible_body


def test_interactive_html_position_evidence_is_inside_details() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    card = _first_position_card(body)
    details = _section(card, "事实依据", "</details>") + "</details>"

    assert "<strong>东东:</strong>" in card
    assert "<strong>西西:</strong>" in card
    assert "<strong>悠悠:</strong>" in card
    assert "<strong>东东:</strong>" not in details
    assert "<strong>西西:</strong>" not in details
    assert "<strong>悠悠:</strong>" not in details
    assert "委员会讨论" in card
    assert "Committee reviewed supplied context." in details


def test_interactive_html_decision_card_still_has_collapsible_evidence_details() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    card = _first_position_card(body)

    assert '<details style="margin-top: 12px;">' in card
    assert "事实依据" in _section(card, "<details", "</details>")
    assert "Committee reviewed supplied context." in _section(
        card,
        "<details",
        "</details>",
    )


def test_interactive_html_trim_card_includes_actionable_sizing_section() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    visible_body = _first_position_card(body)

    assert "当前状态:</strong> 仓位偏高" in visible_body
    assert "建议动作:</strong> 减仓复核" in visible_body
    assert "参考股数:</strong> 具体股数需人工确认" in visible_body
    assert "目标仓位:</strong> 具体比例需人工确认" in visible_body
    assert "执行方式:</strong> 建议分批复核，不自动交易" in visible_body


def test_interactive_html_sell_card_includes_share_guidance_fallback() -> None:
    report = _sample_report()
    sell_decision = replace(
        report.position_decisions[0],
        recommendation=PositionRecommendation.SELL,
        final_rationale="Exit risk is elevated.",
    )
    body = render_investment_research_report_interactive_html(
        replace(report, position_decisions=(sell_decision,)),
        language="zh",
    )
    visible_body = _first_position_card(body)

    assert "卖出复核" in visible_body
    assert "当前状态:</strong> 风险偏高" in visible_body
    assert "参考股数:</strong> 具体股数需人工确认" in visible_body


def test_interactive_html_stable_holdings_section_is_absent() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )

    assert ">3. 稳定持仓</h2>" not in body
    assert "展开稳定持仓" not in body
    assert "MSFT: 继续持有" not in body


def test_interactive_html_raw_evidence_is_bottom_details() -> None:
    body = render_investment_research_report_interactive_html(
        _sample_report(),
        language="zh",
    )
    raw_section = _section(body, ">5. 原始证据</h2>", None)

    assert body.rfind(">5. 原始证据</h2>") > body.rfind(">4. 市场概览</h2>")
    assert "<details" in raw_section
    assert "<summary" in raw_section
    assert (
        "Report evidence: Research assembled from provider-neutral services."
        in raw_section
    )
    assert raw_section.index("<details") < raw_section.index(
        "Report evidence: Research assembled from provider-neutral services."
    )


def test_interactive_html_hides_sensitive_portfolio_values() -> None:
    body = render_investment_research_report_interactive_html(_sample_report())

    assert "12500" not in body
    assert "12,500" not in body
    assert "500" not in body
    assert "$500" not in body
    assert "$1,200.00" not in body
    assert "10 shares" not in body
    assert "10 股" not in body


def test_chinese_interactive_html_raw_evidence_hides_sensitive_portfolio_terms() -> None:
    report = _sample_report()
    sensitive_ticker = replace(
        report.ticker_reports[0],
        summary="NVDA 持仓市值为 1200，持有 10 股。",
        findings=(
            ResearchFinding(
                summary="现金余额 500，成本 900，盈亏 300。",
                source="portfolio",
            ),
        ),
        evidence_notes=("总资产 12500，总市值 12000。",),
        source_summaries=("组合现金为 500。",),
    )
    sensitive_report = replace(
        report,
        ticker_reports=(sensitive_ticker, *report.ticker_reports[1:]),
        evidence_notes=("组合持仓市值和现金余额来自账户。",),
        source_summaries=("总资产快照。",),
    )

    body = render_investment_research_report_interactive_html(
        sensitive_report,
        language="zh",
    )
    raw_section = _section(body, ">5. 原始证据</h2>", None)

    assert "Services growth." in raw_section
    for sensitive_term in ("市值", "股", "现金余额"):
        assert sensitive_term not in raw_section


def test_interactive_html_escapes_dynamic_text() -> None:
    report = _sample_report()
    dangerous_decision = replace(
        report.position_decisions[0],
        final_rationale='Review <trim> & "rebalance" with Xixi\'s notes.',
        dongdong_opinion='Upside < catalyst & "AI"',
        xixi_opinion="Margin > cost & valuation",
        youyou_opinion='Risk "drawdown" < 10% & rising',
        factual_evidence=('Evidence <tag> & "quoted" \'single\'',),
    )
    dangerous_report = replace(
        report,
        title='Morning <Report> & "Alpha"',
        market_summary="Market < breadth > & volatility",
        position_decisions=(dangerous_decision, *report.position_decisions[1:]),
    )

    body = render_investment_research_report_interactive_html(dangerous_report)

    assert "&lt;Report&gt; &amp; &quot;Alpha&quot;" in body
    assert "Review &lt;trim&gt; &amp; &quot;rebalance&quot;" in body
    assert "Xixi&#x27;s notes." in body
    assert "Evidence &lt;tag&gt; &amp; &quot;quoted&quot; &#x27;single&#x27;" in body
    assert 'Review <trim> & "rebalance"' not in body


def _sample_report(
    mode: ReportMode | str = ReportMode.MORNING,
) -> InvestmentResearchReport:
    nvda = ResearchTickerReport(
        ticker="NVDA",
        summary="NVDA is both a portfolio holding and watchlist research item.",
        bull_case=("Datacenter demand.",),
        bear_case=("Export controls.",),
        risks=(
            ResearchRisk(
                "Export controls.",
                evidence_notes=("Watchlist user thesis and notes.",),
            ),
        ),
        catalysts=(
            ResearchCatalyst(
                "Datacenter demand.",
                horizon="next report cycle",
                evidence_notes=("Watchlist user thesis and notes.",),
            ),
        ),
        findings=(
            ResearchFinding(
                summary="NVDA position value is $1,200.00.",
                source="portfolio",
                evidence_notes=("Position context.",),
            ),
        ),
        source_summaries=("portfolio: current holding facts",),
        evidence_notes=("Existing portfolio holding.",),
    )
    aapl = ResearchTickerReport(
        ticker="AAPL",
        summary="Services mix can support margins.",
        bull_case=("Services growth.",),
        bear_case=("China demand risk.",),
        risks=(ResearchRisk("China demand risk."),),
        catalysts=(
            ResearchCatalyst(
                "Services growth.",
                horizon="next quarter",
                evidence_notes=("Watchlist user thesis and notes.",),
            ),
        ),
    )
    return InvestmentResearchReport(
        ticker_reports=(nvda, aapl),
        mode=mode,
        generated_at=GENERATED_AT,
        portfolio_context=PortfolioSnapshot(
            source="portfolio",
            fetched_at=GENERATED_AT,
            account_id="main",
            total_equity=12500,
            total_market_value=12000,
            total_cash=500,
            cash_balance=500,
            total_value=12500,
            positions=(
                PortfolioPosition(
                    symbol="NVDA",
                    quantity=10,
                    market_value=1200,
                    weight=0.096,
                ),
            ),
            allocation_by_symbol=(
                PortfolioAllocationContextItem(
                    category="NVDA",
                    value=1200,
                    percent=0.096,
                ),
                PortfolioAllocationContextItem(
                    category="Cash",
                    value=500,
                    percent=0.04,
                ),
            ),
        ),
        committee_opinions=(
            ResearchCommitteeOpinion(
                persona_id="dongdong",
                display_name="Dongdong",
                role_title="Chief Growth Officer",
                stance="bullish",
                reasoning_summary="Upside is supported by identifiable catalysts.",
                evidence_considered=("Datacenter demand.",),
                key_concern="Export controls.",
                suggested_action="Keep HOLD as advisory guidance.",
                responsibility="Identify durable growth.",
                viewpoint="Look for upside.",
                risk_posture="Optimistic but evidence-based.",
                evidence_requirements=("Catalyst evidence.",),
                writing_style="optimistic_evidence_based",
            ),
        ),
        committee_consensus=ResearchCommitteeConsensus(
            final_action="hold",
            confidence="medium",
            horizon="3-6 months",
            rationale="Committee weighed evidence, risks, and catalysts.",
            final_risk_posture="Balanced and advisory only.",
            todays_suggested_actions=(
                "NVDA: HOLD (medium confidence) over 3-6 months; human investor decides.",
                "AAPL: WATCH (medium confidence) over 3-6 months; human investor decides.",
            ),
        ),
        committee_portfolio_views=(
            ResearchCommitteePortfolioView(
                agent_name="Yoyo",
                role="Chief Risk Officer",
                portfolio_view="Portfolio concentration should stay visible.",
            ),
        ),
        position_decisions=(
            _position_decision(
                "NVDA",
                recommendation=PositionRecommendation.TRIM,
                action_required=True,
                urgency=DecisionUrgency.HIGH,
                confidence=ConfidenceLevel.HIGH,
                human_review_required=True,
            ),
            _position_decision(
                "MSFT",
                recommendation=PositionRecommendation.HOLD,
                action_required=False,
                urgency=DecisionUrgency.LOW,
                confidence=ConfidenceLevel.MEDIUM,
                human_review_required=False,
            ),
        ),
        portfolio_decision_summary=PortfolioDecisionSummary(
            overall_portfolio_view="Portfolio remains balanced.",
            concentration_risks=("NVDA concentration should stay visible.",),
            sector_exposure_notes=("Technology remains overweight.",),
            cash_allocation_notes=("Cash is available for review-approved actions.",),
            action_items=("NVDA: trim review recommended.",),
            no_action_positions=("MSFT",),
        ),
        new_opportunities=(
            NewOpportunity(
                symbol="AMD",
                company_name="Advanced Micro Devices",
                opportunity_type="watchlist",
                rationale="Review as an AI infrastructure alternative.",
                risks=("Competitive pressure remains material.",),
                suggested_action=PositionRecommendation.WATCH,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ),
        source_summaries=("portfolio: current holding facts",),
        evidence_notes=("Research assembled from provider-neutral services.",),
    )


def _position_decision(
    symbol: str,
    *,
    recommendation: PositionRecommendation,
    action_required: bool,
    urgency: DecisionUrgency,
    confidence: ConfidenceLevel,
    human_review_required: bool,
) -> PositionDecision:
    return PositionDecision(
        symbol=symbol,
        company_name=f"{symbol} Inc.",
        recommendation=recommendation,
        action_required=action_required,
        urgency=urgency,
        final_rationale="Committee recommends reviewing the position.",
        dongdong_opinion="Opportunity remains attractive.",
        xixi_opinion="Fundamentals remain strong.",
        youyou_opinion="Sizing risk requires monitoring.",
        factual_evidence=("Committee reviewed supplied context.",),
        risks=("Monitor valuation risk.",),
        confidence=confidence,
        human_review_required=human_review_required,
    )


def _section(body: str, start: str, end: str | None) -> str:
    start_index = body.index(start)
    end_index = len(body) if end is None else body.index(end, start_index)
    return body[start_index:end_index]


def _first_position_card(body: str) -> str:
    return _section(
        body,
        '<details style="background: #ffffff;',
        f"{HTML_H2_STYLE}3. 新机会</h2>",
    )


def _first_html_card(body: str) -> str:
    return _first_position_card(body)


def _position_card_summary(card: str) -> str:
    return _section(card, "<summary", "</summary>") + "</summary>"


def _without_inner_html_details(card: str) -> str:
    visible_parts: list[str] = []
    remaining = card
    marker = '<details style="margin-top: 12px;">'
    while marker in remaining:
        before, after_start = remaining.split(marker, 1)
        visible_parts.append(before)
        _, remaining = after_start.split("</details>", 1)
    visible_parts.append(remaining)
    return "".join(visible_parts)


def _without_details(body: str) -> str:
    visible_parts: list[str] = []
    remaining = body
    while "<details>" in remaining:
        before, after_start = remaining.split("<details>", 1)
        visible_parts.append(before)
        _, remaining = after_start.split("</details>", 1)
    visible_parts.append(remaining)
    return "".join(visible_parts)


def _without_html_details(body: str) -> str:
    visible_parts: list[str] = []
    remaining = body
    while "<details" in remaining:
        before, after_start = remaining.split("<details", 1)
        visible_parts.append(before)
        _, remaining = after_start.split("</details>", 1)
    visible_parts.append(remaining)
    return "".join(visible_parts)
