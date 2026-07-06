"""Tests for investment research report plain-text rendering."""

from __future__ import annotations

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
)


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


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
