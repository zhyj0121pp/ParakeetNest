"""Tests for provider-neutral investment research report models."""

from __future__ import annotations

from datetime import datetime

import pytest

from parakeetnest.research import (
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchCommitteeConsensus,
    ResearchFactInterpretation,
    ResearchRisk,
    ResearchTickerReport,
)


def test_ticker_report_normalizes_for_email_ready_rendering() -> None:
    ticker_report = ResearchTickerReport(
        ticker=" nvda ",
        summary="Existing holding.",
        bull_case=("AI demand.", " "),
        bear_case=("Margin pressure.",),
        risks=(ResearchRisk("Valuation risk."),),
        catalysts=(ResearchCatalyst("Earnings update.", horizon="next quarter"),),
        source_summaries=("portfolio", ""),
        evidence_notes=("Position context.",),
    )

    assert ticker_report.ticker == "NVDA"
    assert ticker_report.bull_case == ("AI demand.",)
    assert not hasattr(ticker_report, "recommendation")
    assert not hasattr(ticker_report, "confidence")


def test_fact_interpretation_normalizes_supported_valuation_labels() -> None:
    interpretation = ResearchFactInterpretation(
        valuation_label=" Revenue_Multiple_Risk ",
        valuation_summary="EV/Sales is elevated.",
        risk_summary="High beta and valuation risk.",
        catalyst_summary="News is available.",
        profile_summary="Technology software company.",
        evidence_notes=(" valuation: EV/Sales 12 ", ""),
    )

    assert interpretation.valuation_label == "revenue_multiple_risk"
    assert interpretation.evidence_notes == ("valuation: EV/Sales 12",)

    with pytest.raises(ValueError, match="valuation label"):
        ResearchFactInterpretation(valuation_label="mystery")


def test_committee_consensus_requires_committee_judgment_fields() -> None:
    consensus = ResearchCommitteeConsensus(
        final_action="hold",
        confidence="medium",
        horizon="3-6 months",
        rationale="Committee weighed evidence and risks.",
        final_risk_posture="Balanced and advisory only.",
        todays_suggested_actions=("NVDA: HOLD for human review.",),
    )

    assert consensus.final_action == "hold"
    assert consensus.confidence == "medium"

    with pytest.raises(ValueError, match="final action"):
        ResearchCommitteeConsensus(
            final_action="accumulate",
            confidence="medium",
            horizon="3-6 months",
            rationale="Invalid action.",
            final_risk_posture="Advisory only.",
            todays_suggested_actions=("Review.",),
        )


def test_report_generated_timestamp_becomes_timezone_aware() -> None:
    ticker_report = ResearchTickerReport(
        ticker="AAPL",
        summary="Watchlist item.",
        bull_case=("Services growth.",),
        bear_case=("Hardware demand risk.",),
        risks=(ResearchRisk("Hardware demand risk."),),
        catalysts=(ResearchCatalyst("Earnings update."),),
    )

    report = InvestmentResearchReport(
        ticker_reports=(ticker_report,),
        generated_at=datetime(2026, 7, 1, 15, 0),
    )

    assert report.generated_at.tzinfo is not None
    assert report.tickers() == ("AAPL",)
    assert report.mode is ReportMode.MORNING
    assert report.title == "Morning Investment Brief"


def test_report_mode_sets_evening_title() -> None:
    report = InvestmentResearchReport(
        ticker_reports=(
            ResearchTickerReport(
                ticker="NVDA",
                summary="Watchlist item.",
                bull_case=("AI demand.",),
                bear_case=("Valuation risk.",),
                risks=(ResearchRisk("Valuation risk."),),
                catalysts=(ResearchCatalyst("Earnings update."),),
            ),
        ),
        mode="evening",
    )

    assert report.mode is ReportMode.EVENING
    assert report.title == "Evening Investment Review"


def test_invalid_report_mode_returns_clear_error() -> None:
    with pytest.raises(ValueError, match="report mode must be morning or evening"):
        InvestmentResearchReport(ticker_reports=(), mode="midday")
