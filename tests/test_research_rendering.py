"""Tests for investment research report plain-text rendering."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.research import (
    InvestmentResearchReport,
    InvestmentResearchReportRenderer,
    RecommendationType,
    ResearchCatalyst,
    ResearchCommitteeOpinion,
    ResearchFinding,
    ResearchRecommendation,
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
    assert "Investment Research Report\n" in body
    assert "Generated At: 2026-07-01T15:00:00+00:00" in body
    assert "Tickers: NVDA, AAPL" in body
    assert "Executive Summary" in body
    assert "- Coverage: 2 ticker(s)." in body
    assert "- Actions: HOLD: 1, WATCH: 1." in body
    assert "Ticker Reports" in body
    assert "Recommendations" in body
    assert "Risks" in body
    assert "Catalysts" in body
    assert "Dongdong's Opinion (Chief Growth Officer)" in body
    assert "- Stance: bullish" in body
    assert "- Reasoning: Upside is supported by identifiable catalysts." in body
    assert "- Evidence:" in body
    assert "  - Datacenter demand." in body
    assert "- Concern: Export controls." in body
    assert "- Suggested Action: Keep HOLD as advisory guidance." in body
    assert "Evidence Notes" in body
    assert "NVDA: HOLD | confidence high | horizon 3-6 months" in body
    assert "AAPL: WATCH | confidence medium | horizon 1-2 quarters" in body
    assert "Every recommendation" not in body


def test_renderer_includes_recommendation_contract_details() -> None:
    body = render_investment_research_report(_sample_report())

    assert "  Evidence:" in body
    assert "    - Portfolio holding with positive unrealized return." in body
    assert "  Risks:" in body
    assert "    - Export controls." in body
    assert "  Catalysts:" in body
    assert "    - Datacenter demand." in body
    assert "  Rationale: Maintain exposure while catalysts remain intact." in body


def test_renderer_collects_evidence_notes_without_provider_coupling() -> None:
    body = InvestmentResearchReportRenderer().render(_sample_report())

    assert "  Report Notes:" in body
    assert "    - Research assembled from provider-neutral services." in body
    assert "  NVDA Notes:" in body
    assert "    - Existing portfolio holding." in body
    assert "  NVDA Finding Evidence (portfolio):" in body
    assert "    - Position context." in body
    assert "  NVDA Risk Evidence:" in body
    assert "    - Watchlist bear case." in body
    assert "  NVDA Catalyst Evidence:" in body
    assert "    - Watchlist bull case." in body


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
    assert "- No recommendations." in body
    assert "- No risks." in body
    assert "- No catalysts." in body
    assert "    - No tickers requested." in body


def _sample_report() -> InvestmentResearchReport:
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
        recommendation=ResearchRecommendation(
            action=RecommendationType.HOLD,
            confidence="high",
            horizon="3-6 months",
            evidence=("Portfolio holding with positive unrealized return.",),
            risks=("Export controls.",),
            catalysts=("Datacenter demand.",),
            rationale="Maintain exposure while catalysts remain intact.",
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
        recommendation=ResearchRecommendation(
            action=RecommendationType.WATCH,
            confidence="medium",
            horizon="1-2 quarters",
            evidence=("Watchlist thesis exists.",),
            risks=("China demand risk.",),
            catalysts=("Services growth.",),
        ),
    )
    return InvestmentResearchReport(
        ticker_reports=(nvda, aapl),
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
        source_summaries=("portfolio: current holding context",),
        evidence_notes=("Research assembled from provider-neutral services.",),
    )
