"""Tests for portfolio-level position decision workflow service."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from parakeetnest.context import (
    KnowledgeBaseSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    NewsContext,
    NewsItem,
    ValuationContextItem,
    ValuationContextSnapshot,
)
from parakeetnest.decision import (
    ConfidenceLevel,
    DecisionUrgency,
    PositionDecision,
    PositionRecommendation,
)
from parakeetnest.services import PortfolioPositionDecisionWorkflowService


@dataclass(frozen=True)
class ProviderNeutralPosition:
    symbol: str
    name: str
    quantity: float
    market_value: float
    weight: float


@dataclass(frozen=True)
class SnapshotLike:
    positions: tuple[ProviderNeutralPosition, ...]


@dataclass(frozen=True)
class HoldingsSnapshotLike:
    holdings: tuple[ProviderNeutralPosition, ...]


@dataclass
class FakePositionDecisionWorkflow:
    calls: list[dict[str, object]] = field(default_factory=list)

    def run(self, position: object, **inputs: object) -> PositionDecision:
        self.calls.append({"position": position, **inputs})
        return _decision(symbol=position.symbol)  # type: ignore[attr-defined]


def test_runs_one_position_workflow_once_per_holding() -> None:
    workflow = FakePositionDecisionWorkflow()
    positions = (_position("NVDA"), _position("MSFT"), _position("AMD"))

    decisions = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run(positions)

    assert len(workflow.calls) == 3
    assert tuple(call["position"] for call in workflow.calls) == positions
    assert tuple(decision.symbol for decision in decisions) == ("NVDA", "MSFT", "AMD")


def test_preserves_input_position_order() -> None:
    workflow = FakePositionDecisionWorkflow()
    positions = (_position("MSFT"), _position("NVDA"), _position("AAPL"))

    decisions = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run(positions)

    assert tuple(decision.symbol for decision in decisions) == ("MSFT", "NVDA", "AAPL")


def test_returns_tuple_of_position_decisions() -> None:
    workflow = FakePositionDecisionWorkflow()

    decisions = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run((_position("NVDA"),))

    assert isinstance(decisions, tuple)
    assert all(isinstance(decision, PositionDecision) for decision in decisions)


def test_accepts_plain_iterable_of_positions() -> None:
    workflow = FakePositionDecisionWorkflow()
    positions = [_position("NVDA"), _position("MSFT")]

    decisions = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run(iter(positions))

    assert tuple(call["position"] for call in workflow.calls) == tuple(positions)
    assert tuple(decision.symbol for decision in decisions) == ("NVDA", "MSFT")


def test_accepts_snapshot_like_object_with_positions() -> None:
    workflow = FakePositionDecisionWorkflow()
    snapshot = SnapshotLike(positions=(_position("NVDA"), _position("MSFT")))

    decisions = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run(snapshot)

    assert tuple(call["position"] for call in workflow.calls) == snapshot.positions
    assert tuple(decision.symbol for decision in decisions) == ("NVDA", "MSFT")


def test_accepts_snapshot_like_object_with_holdings() -> None:
    workflow = FakePositionDecisionWorkflow()
    snapshot = HoldingsSnapshotLike(holdings=(_position("NVDA"), _position("MSFT")))

    decisions = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run(snapshot)

    assert tuple(call["position"] for call in workflow.calls) == snapshot.holdings
    assert tuple(decision.symbol for decision in decisions) == ("NVDA", "MSFT")


def test_passes_shared_inputs_into_each_position_workflow_run() -> None:
    workflow = FakePositionDecisionWorkflow()
    market = MarketSnapshot(
        source="already-available-market",
        points=(MarketDataPoint(symbol="NVDA", source="already-available-market"),),
    )
    news = NewsContext(
        source="already-available-news",
        items=(NewsItem(symbol="NVDA", title="NVIDIA update", source="news"),),
    )
    valuation = ValuationContextSnapshot(
        source="already-available-valuation",
        items=(
            ValuationContextItem(
                symbol="NVDA",
                as_of_date=date(2026, 7, 6),
                metrics={"fair_value": 925},
            ),
        ),
    )
    knowledge_base = KnowledgeBaseSnapshot(
        research_notes=("NVDA thesis remains intact.",)
    )

    PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    ).run(
        (_position("NVDA"), _position("MSFT")),
        market=market,
        news=news,
        valuation=valuation,
        knowledge_base=knowledge_base,
        relevant_research=("Thesis remains intact.",),
        risk_notes=("Sizing risk.",),
        valuation_notes=("Premium valuation.",),
        momentum_notes=("Positive trend.",),
        portfolio_notes=("Largest holding.",),
    )

    for call in workflow.calls:
        assert call["market"] is market
        assert call["news"] is news
        assert call["valuation"] is valuation
        assert call["knowledge_base"] is knowledge_base
        assert call["relevant_research"] == ("Thesis remains intact.",)
        assert call["risk_notes"] == ("Sizing risk.",)
        assert call["valuation_notes"] == ("Premium valuation.",)
        assert call["momentum_notes"] == ("Positive trend.",)
        assert call["portfolio_notes"] == ("Largest holding.",)


def test_dependencies_can_be_replaced_with_fakes() -> None:
    workflow = FakePositionDecisionWorkflow()
    service = PortfolioPositionDecisionWorkflowService(
        position_decision_workflow=workflow,  # type: ignore[arg-type]
    )

    decisions = service((_position("AMD"),))

    assert len(workflow.calls) == 1
    assert decisions[0].symbol == "AMD"


def test_does_not_call_providers_directly() -> None:
    imported_modules, source = _workflow_imports_and_source()

    assert all("provider" not in module for module in imported_modules)
    assert "registry" not in source
    assert "openai" not in source
    assert "anthropic" not in source
    assert "claude" not in source
    assert "gemini" not in source
    assert "robinhood" not in source
    assert "yahoo" not in source


def test_does_not_generate_portfolio_summary() -> None:
    _, source = _workflow_imports_and_source()

    assert "PortfolioDecisionSummary" not in source
    assert "portfolio_summary" not in source


def test_does_not_generate_morning_report() -> None:
    _, source = _workflow_imports_and_source()

    assert "morning" not in source.lower()
    assert "daily" not in source.lower()
    assert "report" not in source.lower()
    assert "composer" not in source.lower()
    assert "render" not in source.lower()


def _position(symbol: str = "NVDA") -> ProviderNeutralPosition:
    return ProviderNeutralPosition(
        symbol=symbol,
        name=f"{symbol} Inc.",
        quantity=2,
        market_value=1840,
        weight=0.25,
    )


def _decision(symbol: str = "NVDA") -> PositionDecision:
    return PositionDecision(
        symbol=symbol,
        company_name=f"{symbol} Inc.",
        recommendation=PositionRecommendation.WATCH,
        action_required=False,
        urgency=DecisionUrgency.LOW,
        final_rationale="Committee recommends watching the position.",
        dongdong_opinion="Opportunity remains attractive.",
        xixi_opinion="Fundamentals remain strong.",
        youyou_opinion="Sizing risk requires monitoring.",
        factual_evidence=("Committee reviewed supplied context.",),
        risks=("Monitor valuation risk.",),
        confidence=ConfidenceLevel.MEDIUM,
        human_review_required=False,
    )


def _workflow_imports_and_source() -> tuple[list[str], str]:
    source_path = Path("src/parakeetnest/services/portfolio_position_decision_workflow.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
    return imported_modules, source
