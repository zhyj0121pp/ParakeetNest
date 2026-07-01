"""Tests for investment research report plain-text rendering."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.research import (
    InvestmentResearchReport,
    InvestmentResearchReportRenderer,
    ReportMode,
    ResearchCatalyst,
    ResearchCommitteeConsensus,
    ResearchCommitteeOpinion,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
    render_investment_research_report,
)


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)


def test_renderer_produces_plain_text_email_report_with_required_sections() -> None:
    report = _sample_report()
    renderer = InvestmentResearchReportRenderer()

    body = renderer.render(report)

    assert body == renderer.render(report)
    assert body.endswith("\n")
    assert "# " not in body
    assert body.startswith("Header\n")
    assert "Morning Investment Brief\n" in body
    assert "Report Mode: morning" in body
    assert "Generated At: 2026-07-01T15:00:00+00:00" in body
    assert "Tickers: NVDA, AAPL" in body
    assert "Market Setup" in body
    assert "Portfolio Watch" in body
    assert "Watchlist Focus" in body
    assert "Today’s Focus" in body
    assert "- Coverage: 2 ticker(s)." in body
    assert "- Committee view: HOLD (medium confidence)." in body
    assert "Factual Ticker Context" in body
    assert "Recommendations" not in body
    assert "Key Risks" in body
    assert "Upcoming Catalysts" in body
    assert "Dongdong’s Opportunity View (Chief Growth Officer)" in body
    assert "- Stance: bullish" in body
    assert "- Reasoning: Upside is supported by identifiable catalysts." in body
    assert "- Evidence:" in body
    assert "  - Datacenter demand." in body
    assert "- Concern: Export controls." in body
    assert "- Suggested Action: Keep HOLD as advisory guidance." in body
    assert "Evidence Notes" in body
    assert "- Final Action: HOLD" in body
    assert "- medium" in body
    assert "NVDA: HOLD (medium confidence) over 3-6 months; human investor decides." in body
    assert "Every recommendation" not in body


def test_renderer_includes_committee_consensus_contract_details() -> None:
    body = render_investment_research_report(_sample_report())

    assert "Committee Consensus" in body
    assert "- Final Action: HOLD" in body
    assert "- Horizon: 3-6 months" in body
    assert "- Final Risk Posture: Balanced and advisory only." in body
    assert "- Rationale: Committee weighed evidence, risks, and catalysts." in body
    assert "Today's Suggested Actions" in body


def test_renderer_supports_evening_review_mode() -> None:
    report = _sample_report(mode=ReportMode.EVENING)
    body = InvestmentResearchReportRenderer().render(report)

    assert "Evening Investment Review\n" in body
    assert "Report Mode: evening" in body
    assert "Market Recap" in body
    assert "Portfolio Review" in body
    assert "Watchlist Review" in body
    assert "What Changed" in body
    assert "Dongdong’s Opportunity Review (Chief Growth Officer)" in body
    assert "Tomorrow’s Focus" in body
    assert "Suggested Follow-ups" in body
    assert "Today's Suggested Actions" not in body


def test_renderer_collects_evidence_notes_without_provider_coupling() -> None:
    body = InvestmentResearchReportRenderer().render(_sample_report())

    assert "  Report Notes:" in body
    assert "    - Research assembled from provider-neutral services." in body
    assert "  NVDA Finding Evidence (portfolio):" in body
    assert "    - Position context." in body
    assert "  NVDA Risk Evidence:" in body
    assert "    - Watchlist bear case." in body
    assert "  NVDA Catalyst Evidence:" in body
    assert "    - Watchlist bull case." in body


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

    assert "Tickers: None" in body
    assert "- No ticker reports were generated." in body
    assert "- No ticker reports." in body
    assert "- No risks." in body
    assert "- No catalysts." in body
    assert "    - No tickers requested." in body


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
        source_summaries=("portfolio: current holding context",),
        evidence_notes=("Research assembled from provider-neutral services.",),
    )
