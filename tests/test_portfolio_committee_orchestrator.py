"""Tests for the portfolio committee orchestration entry point."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from parakeetnest.committee import AgentResult, MeetingContext, MeetingStatus
from parakeetnest.context import ContextRequest
from parakeetnest.context.models import (
    ContextMetadata,
    MeetingContext as ResearchMeetingContext,
    PortfolioSnapshot,
)
from parakeetnest.context.provider import ContextProviderResult
from parakeetnest.portfolio.orchestrator import PortfolioCommitteeOrchestrator


EXPECTED_AGENT_IDS = (
    "portfolio_manager",
    "portfolio_risk_manager",
    "sector_analyst",
    "macro_strategist",
)

EXPECTED_AGENT_NAMES = (
    "Portfolio Manager",
    "Risk Manager",
    "Sector Analyst",
    "Macro Strategist",
)


@dataclass
class RecordingPortfolioContextProvider:
    calls: list[ContextRequest] = field(default_factory=list)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        self.calls.append(request)
        return ContextProviderResult(
            provider_name="portfolio",
            partial_context=ResearchMeetingContext(
                request=request,
                metadata=ContextMetadata(sources=("portfolio",)),
                portfolio=PortfolioSnapshot(
                    source="portfolio",
                    account_id="test-account",
                    total_equity=100000.0,
                    symbols=("AAPL", "MSFT"),
                ),
            ),
        )


@dataclass
class FailingPortfolioContextProvider:
    message: str = "portfolio context unavailable"

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        raise RuntimeError(self.message)


@dataclass
class RecordingAgentRuntime:
    memory_service: object | None = None
    prompt_renderer: object | None = None
    calls: list[tuple[str, MeetingContext]] = field(default_factory=list)

    def run(self, agent, context: MeetingContext) -> AgentResult:
        self.calls.append((agent.agent_id, context))
        payload = {
            "agent_name": agent.name,
            "role": agent.role,
            "portfolio_view": f"{agent.name} reviewed the portfolio.",
            "advisory_action": "Monitor portfolio exposure; do not execute trades.",
            "confidence": "medium",
            "horizon": "3_months",
            "evidence": [{"summary": "Portfolio context reviewed.", "source": "unit_test"}],
            "risks": ["Concentration risk."],
            "catalysts": ["Macro update."],
        }
        return AgentResult(
            agent_name=agent.name,
            role=agent.role,
            content=json.dumps(payload, sort_keys=True),
            agent_id=agent.agent_id,
            ticker=context.ticker,
        )


def test_orchestrator_can_be_created() -> None:
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=RecordingAgentRuntime(),
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    assert tuple(agent.agent_id for agent in orchestrator.agents) == EXPECTED_AGENT_IDS


def test_portfolio_context_provider_is_called() -> None:
    provider = RecordingPortfolioContextProvider()
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=RecordingAgentRuntime(),
        portfolio_context_provider=provider,
    )

    result = orchestrator.run("Review portfolio risk.", ticker="PORTFOLIO")

    assert len(provider.calls) == 1
    assert provider.calls[0].question == "Review portfolio risk."
    assert provider.calls[0].symbols == ("PORTFOLIO",)
    assert provider.calls[0].include_portfolio is True
    assert result.portfolio_context.portfolio is not None


def test_all_portfolio_agents_are_run_and_responses_are_collected() -> None:
    runtime = RecordingAgentRuntime()
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=runtime,
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    result = orchestrator.run("Review the portfolio.")

    assert [agent_id for agent_id, _context in runtime.calls] == list(EXPECTED_AGENT_IDS)
    assert [agent.agent_name for agent in result.agent_results] == list(
        EXPECTED_AGENT_NAMES
    )
    assert [agent.agent_id for agent in result.agent_results] == list(EXPECTED_AGENT_IDS)
    assert all("advisory_action" in agent.content for agent in result.agent_results)


def test_later_agent_context_includes_previous_agent_results() -> None:
    runtime = RecordingAgentRuntime()
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=runtime,
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    orchestrator.run("Review the portfolio.")

    previous_counts = [len(context.previous_agent_results) for _id, context in runtime.calls]
    assert previous_counts == [0, 1, 2, 3]


def test_result_includes_portfolio_committee_metadata() -> None:
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=RecordingAgentRuntime(),
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    result = orchestrator.run("Review the portfolio.")

    assert result.status is MeetingStatus.COMPLETED
    assert result.metadata["committee"] == "portfolio"
    assert result.metadata["mode"] == "advisory_analytical"
    assert result.metadata["agent_ids"] == list(EXPECTED_AGENT_IDS)
    assert result.metadata["agent_names"] == list(EXPECTED_AGENT_NAMES)
    assert result.metadata["non_execution"] is True


def test_memory_service_is_optional() -> None:
    runtime = RecordingAgentRuntime()
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=runtime,
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    result = orchestrator.run("Review the portfolio.")

    assert orchestrator.memory_service is None
    assert result.status is MeetingStatus.COMPLETED


def test_memory_service_is_integrated_with_runtime_when_provided() -> None:
    memory_service = object()
    runtime = RecordingAgentRuntime()

    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=runtime,
        portfolio_context_provider=RecordingPortfolioContextProvider(),
        memory_service=memory_service,
    )

    assert orchestrator.memory_service is memory_service
    assert runtime.memory_service is memory_service


def test_runtime_memory_service_is_reused_when_not_explicitly_provided() -> None:
    memory_service = object()
    runtime = RecordingAgentRuntime(memory_service=memory_service)

    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=runtime,
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    assert orchestrator.memory_service is memory_service


def test_provider_context_errors_propagate_clearly() -> None:
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=RecordingAgentRuntime(),
        portfolio_context_provider=FailingPortfolioContextProvider(),
    )

    with pytest.raises(RuntimeError, match="portfolio context unavailable"):
        orchestrator.run("Review the portfolio.")


def test_no_trade_execution_behavior_exists() -> None:
    runtime = RecordingAgentRuntime()
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=runtime,
        portfolio_context_provider=RecordingPortfolioContextProvider(),
    )

    result = orchestrator.run("Review the portfolio.")

    forbidden_attributes = (
        "execute_trade",
        "place_order",
        "submit_order",
        "rebalance",
        "robinhood",
        "brokerage_api",
    )
    for attribute in forbidden_attributes:
        assert not hasattr(orchestrator, attribute)
        assert not hasattr(runtime, attribute)

    result_text = json.dumps(result.metadata).lower()
    assert "non_execution" in result_text
    assert result.metadata["non_execution"] is True
