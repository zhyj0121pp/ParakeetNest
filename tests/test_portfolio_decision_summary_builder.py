"""Tests for deterministic portfolio decision summary building."""

from __future__ import annotations

import ast
from pathlib import Path

from parakeetnest.decision import (
    ConfidenceLevel,
    DecisionUrgency,
    PortfolioDecisionSummary,
    PositionDecision,
    PositionRecommendation,
)
from parakeetnest.services import PortfolioDecisionSummaryBuilder


def test_action_required_decisions_become_action_items() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(
        (
            _decision(
                "NVDA",
                recommendation=PositionRecommendation.TRIM,
                action_required=True,
                urgency=DecisionUrgency.HIGH,
            ),
            _decision("MSFT", action_required=False),
        )
    )

    assert len(summary.action_items) == 1
    assert summary.action_items[0].startswith("NVDA: trim")
    assert "MSFT" not in " ".join(summary.action_items)


def test_non_action_decisions_become_no_action_positions() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(
        (
            _decision("NVDA", action_required=True, urgency=DecisionUrgency.MEDIUM),
            _decision("MSFT", action_required=False),
            _decision("AAPL", action_required=False),
        )
    )

    assert summary.no_action_positions == ("MSFT", "AAPL")


def test_high_urgency_decisions_contribute_to_concentration_risks() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(
        (
            _decision(
                "NVDA",
                action_required=True,
                urgency=DecisionUrgency.HIGH,
                risks=("Oversized AI exposure.", "Valuation compression risk."),
            ),
            _decision(
                "MSFT",
                action_required=False,
                urgency=DecisionUrgency.LOW,
                risks=("Cloud execution risk.",),
            ),
        )
    )

    assert summary.concentration_risks == (
        "NVDA high urgency: Oversized AI exposure.",
        "NVDA high urgency: Valuation compression risk.",
    )


def test_optional_sector_exposure_notes_are_preserved() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(
        (),
        sector_exposure_notes=(" Technology remains overweight. ",),
    )

    assert summary.sector_exposure_notes == ("Technology remains overweight.",)


def test_optional_cash_allocation_notes_are_preserved() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(
        (),
        cash_allocation_notes=(" Cash is available for review-approved actions. ",),
    )

    assert summary.cash_allocation_notes == (
        "Cash is available for review-approved actions.",
    )


def test_summary_handles_empty_decisions() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(())

    assert isinstance(summary, PortfolioDecisionSummary)
    assert summary.overall_portfolio_view == (
        "0 action-required positions; 0 no-action positions; highest urgency: none."
    )
    assert summary.concentration_risks == ()
    assert summary.action_items == ()
    assert summary.no_action_positions == ()


def test_overall_portfolio_view_summarizes_counts_urgency_and_confidence() -> None:
    summary = PortfolioDecisionSummaryBuilder().build(
        (
            _decision(
                "NVDA",
                action_required=True,
                urgency=DecisionUrgency.HIGH,
                confidence=ConfidenceLevel.HIGH,
            ),
            _decision(
                "MSFT",
                action_required=False,
                urgency=DecisionUrgency.LOW,
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ),
        portfolio_notes=("Watch concentration before adding risk.",),
    )

    assert summary.overall_portfolio_view == (
        "1 action-required positions; 1 no-action positions; highest urgency: high; "
        "overall confidence: medium; portfolio context: Watch concentration before "
        "adding risk."
    )


def test_builder_has_no_llm_provider_dependency() -> None:
    _, source = _builder_imports_and_source()

    assert "LLMProvider" not in source
    assert "llm_provider" not in source
    assert "parakeetnest.llm" not in source


def test_builder_has_no_provider_specific_references() -> None:
    imported_modules, source = _builder_imports_and_source()

    provider_terms = (
        "provider",
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "robinhood",
        "yahoo",
        "gmail",
    )
    assert all("provider" not in module for module in imported_modules)
    assert all(term not in source.lower() for term in provider_terms)


def test_builder_does_not_generate_morning_report() -> None:
    _, source = _builder_imports_and_source()

    assert "morning" not in source.lower()
    assert "daily" not in source.lower()
    assert "report" not in source.lower()
    assert "composer" not in source.lower()
    assert "render" not in source.lower()


def _decision(
    symbol: str = "NVDA",
    *,
    recommendation: PositionRecommendation = PositionRecommendation.WATCH,
    action_required: bool = False,
    urgency: DecisionUrgency = DecisionUrgency.LOW,
    risks: tuple[str, ...] = ("Monitor valuation risk.",),
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> PositionDecision:
    if action_required and recommendation is PositionRecommendation.WATCH:
        recommendation = PositionRecommendation.TRIM
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
        risks=risks,
        confidence=confidence,
        human_review_required=action_required,
    )


def _builder_imports_and_source() -> tuple[list[str], str]:
    source_path = Path("src/parakeetnest/services/portfolio_decision_summary.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
    return imported_modules, source
