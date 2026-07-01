"""Tests for provider-neutral investment research report models."""

from __future__ import annotations

from datetime import datetime

import pytest

from parakeetnest.research import (
    ConfidenceLevel,
    InvestmentResearchReport,
    RecommendationType,
    ResearchCatalyst,
    ResearchRecommendation,
    ResearchRisk,
    ResearchTickerReport,
)


def test_ticker_report_normalizes_for_email_ready_rendering() -> None:
    recommendation = ResearchRecommendation(
        action="hold",
        confidence="medium",
        horizon="3-6 months",
        evidence=("Portfolio holding.", ""),
        risks=("Valuation risk.",),
        catalysts=("Earnings update.",),
    )

    ticker_report = ResearchTickerReport(
        ticker=" nvda ",
        summary="Existing holding.",
        bull_case=("AI demand.", " "),
        bear_case=("Margin pressure.",),
        risks=(ResearchRisk("Valuation risk."),),
        catalysts=(ResearchCatalyst("Earnings update.", horizon="next quarter"),),
        recommendation=recommendation,
        source_summaries=("portfolio", ""),
        evidence_notes=("Position context.",),
    )

    assert ticker_report.ticker == "NVDA"
    assert ticker_report.bull_case == ("AI demand.",)
    assert ticker_report.confidence is ConfidenceLevel.MEDIUM
    assert ticker_report.recommendation.action is RecommendationType.HOLD


def test_recommendation_requires_evidence_risks_and_catalysts() -> None:
    with pytest.raises(ValueError, match="evidence is required"):
        ResearchRecommendation(
            action=RecommendationType.WATCH,
            confidence=ConfidenceLevel.LOW,
            horizon="3-6 months",
            evidence=(),
            risks=("Research gap.",),
            catalysts=("Add context.",),
        )

    with pytest.raises(ValueError, match="risks are required"):
        ResearchRecommendation(
            action=RecommendationType.WATCH,
            confidence=ConfidenceLevel.LOW,
            horizon="3-6 months",
            evidence=("Requested ticker.",),
            risks=(),
            catalysts=("Add context.",),
        )

    with pytest.raises(ValueError, match="catalysts are required"):
        ResearchRecommendation(
            action=RecommendationType.WATCH,
            confidence=ConfidenceLevel.LOW,
            horizon="3-6 months",
            evidence=("Requested ticker.",),
            risks=("Research gap.",),
            catalysts=(),
        )


def test_report_generated_timestamp_becomes_timezone_aware() -> None:
    ticker_report = ResearchTickerReport(
        ticker="AAPL",
        summary="Watchlist item.",
        bull_case=("Services growth.",),
        bear_case=("Hardware demand risk.",),
        risks=(ResearchRisk("Hardware demand risk."),),
        catalysts=(ResearchCatalyst("Earnings update."),),
        recommendation=ResearchRecommendation(
            action=RecommendationType.WATCH,
            confidence=ConfidenceLevel.LOW,
            horizon="3-6 months",
            evidence=("Watchlist context.",),
            risks=("Hardware demand risk.",),
            catalysts=("Earnings update.",),
        ),
    )

    report = InvestmentResearchReport(
        ticker_reports=(ticker_report,),
        generated_at=datetime(2026, 7, 1, 15, 0),
    )

    assert report.generated_at.tzinfo is not None
    assert report.tickers() == ("AAPL",)
