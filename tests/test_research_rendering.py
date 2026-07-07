"""Tests for investment research report email-friendly Markdown rendering."""

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
    InteractiveHtmlEmailInvestmentResearchReportRenderer,
    InvestmentResearchReport,
    InvestmentResearchReportRenderer,
    ReportMode,
    ResearchCatalyst,
    ResearchCommitteeConsensus,
    ResearchCommitteeOpinion,
    ResearchCommitteePortfolioView,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
    render_investment_research_report,
    render_investment_research_report_interactive_html_email,
)


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)
HTML_H2_STYLE = (
    '<h2 style="font-size: 20px; margin: 24px 0 10px; color: #111827;">'
)


def test_renderer_produces_email_friendly_morning_markdown() -> None:
    report = _sample_report()
    renderer = InvestmentResearchReportRenderer()

    body = renderer.render(report)

    assert body == renderer.render(report)
    assert body.endswith("\n")
    assert body.startswith("# Morning Investment Report\n")
    assert "## 1. Action Required" in body
    assert "## 2. Position Cards" in body
    assert "## 3. Stable Holdings" in body
    assert "## 4. New Opportunities" in body
    assert "## 5. Market Overview" in body
    assert "## 6. Raw Evidence" in body
    assert "### NVDA — Trim" in body
    assert "**Recommendation:** Trim  " in body
    assert "**Confidence:** High  " in body
    assert "**Rationale:** Committee recommends reviewing the position." in body
    assert "**Dongdong:** Opportunity remains attractive." in body
    assert "**Xixi:** Fundamentals remain strong." in body
    assert "**Youyou:** Sizing risk requires monitoring." in body
    assert "**Final consensus:** Committee recommends reviewing the position. No automatic action. User review recommended." in body
    assert "Recommendations" not in body


def test_morning_report_does_not_use_markdown_tables() -> None:
    body = render_investment_research_report(_sample_report())

    assert "| ---" not in body
    assert "|---" not in body
    assert not any(
        line.strip().startswith("|") and line.strip().endswith("|")
        for line in body.splitlines()
    )


def test_critical_recommendation_fields_are_visible_outside_details() -> None:
    body = render_investment_research_report(_sample_report())
    visible_body = _without_details(body)

    assert "### NVDA — Trim" in visible_body
    assert "**Recommendation:** Trim" in visible_body
    assert "**Confidence:** High" in visible_body
    assert "**Rationale:** Committee recommends reviewing the position." in visible_body
    assert "**Dongdong:** Opportunity remains attractive." in visible_body
    assert "**Xixi:** Fundamentals remain strong." in visible_body
    assert "**Youyou:** Sizing risk requires monitoring." in visible_body
    assert "**Final consensus:**" in visible_body


def test_interactive_html_email_renderer_outputs_standalone_html() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert body == InteractiveHtmlEmailInvestmentResearchReportRenderer().render(
        _sample_report()
    )
    assert body.startswith("<!doctype html>\n<html>\n")
    assert "<body style=" in body
    assert body.endswith("</html>\n")
    assert "## 1. Action Required" not in body


def test_interactive_html_email_uses_inline_card_layout_and_badges() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert 'style="' in body
    assert "border-left: 5px solid #f97316" in body
    assert "border-radius: 10px" in body
    assert ">减仓复核</span>" in body
    assert ">信心：高</span>" in body
    assert ">紧急程度：高</span>" in body
    assert ">需要人工复核</span>" in body
    assert "<script" not in body.lower()
    assert "<style" not in body.lower()
    assert "<link" not in body.lower()


def test_interactive_html_email_uses_chinese_section_titles() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert ">1. 需要处理</h2>" in body
    assert ">2. 持仓决策卡片</h2>" in body
    assert ">3. 稳定持仓</h2>" in body
    assert ">4. 新机会</h2>" in body
    assert ">5. 市场概览</h2>" in body
    assert ">6. 原始证据</h2>" in body


def test_interactive_html_email_uses_chinese_field_labels() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert "<strong>建议:</strong> 减仓复核" in body
    assert "<strong>信心:</strong> 高" in body
    assert "<strong>紧急程度:</strong> 高" in body
    assert "<strong>理由:</strong> Committee recommends reviewing the position." in body
    assert "<strong>最终共识:</strong>" in body
    assert "<strong>东东:</strong> Opportunity remains attractive." in body
    assert "<strong>西西:</strong> Fundamentals remain strong." in body
    assert "<strong>悠悠:</strong> Sizing risk requires monitoring." in body


def test_interactive_html_email_localizes_recommendation_confidence_and_urgency() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert "减仓复核" in body
    assert "继续持有" in body
    assert "继续观察" in body
    assert "信心：高" in body
    assert "信心：中" in body
    assert "紧急程度：高" in body


def test_interactive_html_email_contains_progressive_details_sections() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert "<details" in body
    assert "<summary" in body
    assert "事实依据" in body
    assert "查看稳定持仓" in body
    assert "查看原始证据" in body


def test_interactive_html_critical_fields_are_visible_outside_details() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())
    visible_body = _without_html_details(body)

    assert "NVDA - 减仓复核" in visible_body
    assert "<strong>建议:</strong> 减仓复核" in visible_body
    assert "<strong>信心:</strong> 高" in visible_body
    assert "<strong>紧急程度:</strong> 高" in visible_body
    assert (
        "<strong>理由:</strong> Committee recommends reviewing the position."
        in visible_body
    )
    assert "<strong>最终共识:</strong>" in visible_body
    assert "<strong>东东:</strong> Opportunity remains attractive." in visible_body
    assert "<strong>西西:</strong> Fundamentals remain strong." in visible_body
    assert "<strong>悠悠:</strong> Sizing risk requires monitoring." in visible_body
    assert "<strong>行动与仓位复核</strong>" in visible_body
    assert "<strong>参考股数:</strong> 具体股数需人工确认" in visible_body
    assert "<strong>目标仓位:</strong> 具体比例需人工确认" in visible_body
    assert "<strong>执行方式:</strong> 建议分批复核，不自动交易" in visible_body
    assert "Committee reviewed supplied context." not in visible_body


def test_interactive_html_position_evidence_is_inside_details() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())
    card = _section(body, "<h3", f"{HTML_H2_STYLE}3. 稳定持仓</h2>")
    details = _section(card, "<details", "</details>") + "</details>"

    assert "<strong>东东:</strong>" in card
    assert "<strong>西西:</strong>" in card
    assert "<strong>悠悠:</strong>" in card
    assert "Committee reviewed supplied context." in details
    assert "Committee reviewed supplied context." not in _without_html_details(card)


def test_interactive_html_trim_card_includes_actionable_sizing_section() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())
    visible_body = _without_html_details(body)

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
    body = render_investment_research_report_interactive_html_email(
        replace(report, position_decisions=(sell_decision,))
    )
    visible_body = _without_html_details(body)

    assert "卖出复核" in visible_body
    assert "当前状态:</strong> 风险偏高" in visible_body
    assert "参考股数:</strong> 具体股数需人工确认" in visible_body


def test_interactive_html_stable_holdings_are_inside_details() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())
    stable_section = _section(
        body,
        ">3. 稳定持仓</h2>",
        ">4. 新机会</h2>",
    )

    assert "<details" in stable_section
    assert "<summary" in stable_section
    assert "MSFT: 继续持有" in stable_section
    assert "MSFT: 继续持有" not in _without_html_details(stable_section)


def test_interactive_html_raw_evidence_is_bottom_details() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())
    raw_section = _section(body, ">6. 原始证据</h2>", None)

    assert body.rfind(">6. 原始证据</h2>") > body.rfind(">5. 市场概览</h2>")
    assert "<details" in raw_section
    assert "<summary" in raw_section
    assert (
        "Report evidence: Research assembled from provider-neutral services."
        in raw_section
    )
    assert raw_section.index("<details") < raw_section.index(
        "Report evidence: Research assembled from provider-neutral services."
    )


def test_interactive_html_email_hides_sensitive_portfolio_values() -> None:
    body = render_investment_research_report_interactive_html_email(_sample_report())

    assert "12500" not in body
    assert "12,500" not in body
    assert "500" not in body
    assert "$500" not in body
    assert "$1,200.00" not in body
    assert "10 shares" not in body
    assert "10 股" not in body


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

    body = render_investment_research_report_interactive_html_email(dangerous_report)

    assert "&lt;Report&gt; &amp; &quot;Alpha&quot;" in body
    assert "Review &lt;trim&gt; &amp; &quot;rebalance&quot;" in body
    assert "Xixi&#x27;s notes." in body
    assert "Evidence &lt;tag&gt; &amp; &quot;quoted&quot; &#x27;single&#x27;" in body
    assert 'Review <trim> & "rebalance"' not in body


def test_morning_report_section_order_is_exact() -> None:
    body = render_investment_research_report(_sample_report())

    headings = [
        "## 1. Action Required",
        "## 2. Position Cards",
        "## 3. Stable Holdings",
        "## 4. New Opportunities",
        "## 5. Market Overview",
        "## 6. Raw Evidence",
    ]
    assert [body.index(heading) for heading in headings] == sorted(
        body.index(heading) for heading in headings
    )


def test_action_required_holdings_appear_before_stable_holdings() -> None:
    body = render_investment_research_report(_sample_report())

    assert body.index("### NVDA — Trim") < body.index("## 3. Stable Holdings")
    assert body.index("### NVDA — Trim") < body.index("MSFT: Hold")


def test_stable_holdings_are_collapsed_by_default() -> None:
    body = render_investment_research_report(_sample_report())
    stable_section = _section(body, "## 3. Stable Holdings", "## 4. New Opportunities")

    assert "<details>" in stable_section
    assert "<summary>Stable holdings</summary>" in stable_section
    assert "MSFT: Hold" in stable_section
    assert stable_section.strip().endswith("</details>")


def test_position_card_factual_evidence_is_collapsed_by_default() -> None:
    body = render_investment_research_report(_sample_report())
    card = _section(body, "### NVDA — Trim", "## 3. Stable Holdings")

    assert "<details>" in card
    assert "<summary>Factual evidence</summary>" in card
    assert "- Committee reviewed supplied context." in card
    assert card.strip().endswith("</details>")


def test_each_position_card_includes_committee_member_opinions() -> None:
    body = render_investment_research_report(_sample_report())
    card = _section(body, "### NVDA — Trim", "## 3. Stable Holdings")

    assert "**Dongdong:**" in card
    assert "**Xixi:**" in card
    assert "**Youyou:**" in card


def test_raw_evidence_appears_at_bottom_and_is_collapsible() -> None:
    body = render_investment_research_report(_sample_report())
    raw_section = _section(body, "## 6. Raw Evidence", None)

    assert body.rfind("## 6. Raw Evidence") > body.rfind("## 5. Market Overview")
    assert "<details>" in raw_section
    assert "<summary>Raw evidence</summary>" in raw_section
    assert "- Report evidence: Research assembled from provider-neutral services." in raw_section
    assert raw_section.strip().endswith("</details>")


def test_renderer_supports_evening_review_mode() -> None:
    report = _sample_report(mode=ReportMode.EVENING)
    body = InvestmentResearchReportRenderer().render(report)

    assert "Evening Investment Review\n" in body
    assert "Report Mode: evening" in body
    assert "Market Recap" in body
    assert "Portfolio Review" in body
    assert "Portfolio Summary" in body
    assert "Watchlist Review" in body
    assert "What Changed" in body
    assert "Dongdong’s Opportunity Review (Chief Growth Officer)" in body
    assert "Tomorrow’s Focus" in body
    assert "Suggested Follow-ups" in body
    assert "Today's Suggested Actions" not in body


def test_renderer_displays_portfolio_summary_and_committee_portfolio_view() -> None:
    body = InvestmentResearchReportRenderer().render(_sample_report())

    assert "- Portfolio context: Portfolio review depends on connected portfolio context." in body
    assert "- Portfolio view: Portfolio remains balanced." in body
    assert "- Concentration risk: NVDA concentration should stay visible." in body
    assert "- Sector exposure: Technology remains overweight." in body
    assert "- Cash allocation: Cash is available for review-approved actions." in body


def test_renderer_collects_evidence_notes_without_provider_coupling() -> None:
    body = InvestmentResearchReportRenderer().render(_sample_report())

    assert "- Report evidence: Research assembled from provider-neutral services." in body
    assert "  - Finding: NVDA position value is $1,200.00. (source: portfolio)" in body
    assert "    - Evidence note: Position context." in body
    assert "  - Evidence note: Existing portfolio holding." in body


def test_renderer_does_not_spam_identical_missing_service_notes_per_ticker() -> None:
    report = InvestmentResearchReport(
        ticker_reports=(
            ResearchTickerReport(
                ticker="NVDA",
                summary="NVDA has limited context.",
                bull_case=("No connected bull-case evidence yet.",),
                bear_case=("Insufficient connected research context is the primary risk.",),
                risks=(ResearchRisk("Insufficient connected research context is the primary risk."),),
                catalysts=(ResearchCatalyst("Add thesis and signals."),),
            ),
            ResearchTickerReport(
                ticker="TSLA",
                summary="TSLA has limited context.",
                bull_case=("No connected bull-case evidence yet.",),
                bear_case=("Insufficient connected research context is the primary risk.",),
                risks=(ResearchRisk("Insufficient connected research context is the primary risk."),),
                catalysts=(ResearchCatalyst("Add thesis and signals."),),
            ),
        ),
        generated_at=GENERATED_AT,
        evidence_notes=(
            "No portfolio service connected.",
            "No watchlist service connected.",
            "No intelligence service connected.",
        ),
    )

    body = InvestmentResearchReportRenderer().render(report)

    assert body.count("No portfolio service connected.") == 1
    assert body.count("No watchlist service connected.") == 1
    assert body.count("No intelligence service connected.") == 1


def test_renderer_keeps_report_advisory_only() -> None:
    body = InvestmentResearchReportRenderer().render(_sample_report())

    assert "advisory guidance" in body
    assert "automatic trading" not in body.lower()
    assert "broker" not in body.lower()
    assert "execute trade" not in body.lower()


def test_renderer_handles_empty_report_gracefully() -> None:
    report = InvestmentResearchReport(
        ticker_reports=(),
        generated_at=GENERATED_AT,
        evidence_notes=("No tickers requested.",),
    )

    body = InvestmentResearchReportRenderer().render(report)

    assert "# Morning Investment Report" in body
    assert "- No position decisions currently require user action." in body
    assert "- No action-required position cards available." in body
    assert "- No stable holdings available." in body
    assert "- Report evidence: No tickers requested." in body


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
                evidence_notes=("Watchlist bear case.",),
            ),
        ),
        catalysts=(
            ResearchCatalyst(
                "Datacenter demand.",
                horizon="next report cycle",
                evidence_notes=("Watchlist bull case.",),
            ),
        ),
        findings=(
            ResearchFinding(
                summary="NVDA position value is $1,200.00.",
                source="portfolio",
                evidence_notes=("Position context.",),
            ),
        ),
        source_summaries=("portfolio: current holding context",),
        evidence_notes=("Existing portfolio holding.",),
    )
    aapl = ResearchTickerReport(
        ticker="AAPL",
        summary="Services mix can support margins.",
        bull_case=("Services growth.",),
        bear_case=("China demand risk.",),
        risks=(ResearchRisk("China demand risk."),),
        catalysts=(ResearchCatalyst("Services growth.", horizon="next quarter"),),
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
        source_summaries=("portfolio: current holding context",),
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
