"""Portfolio-specific committee orchestration entry point."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from parakeetnest.committee.agents import PromptBackedCommitteeAgent
from parakeetnest.committee.base import CommitteeAgent
from parakeetnest.committee.models import AgentResult, MeetingContext, MeetingStatus
from parakeetnest.committee.runtime import AgentRuntime
from parakeetnest.context.models import ContextRequest
from parakeetnest.context.models import MeetingContext as ResearchMeetingContext
from parakeetnest.context.provider import ContextProviderResult
from parakeetnest.portfolio.agents import PORTFOLIO_COMMITTEE_AGENT_PROFILES


class PortfolioContextProvider(Protocol):
    """Context provider contract used by the portfolio committee entry point."""

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        """Return portfolio context for the supplied context request."""


@dataclass(frozen=True)
class PortfolioCommitteeResult:
    """Structured advisory output from one portfolio committee run."""

    status: MeetingStatus
    question: str
    ticker: str
    agent_results: tuple[AgentResult, ...]
    metadata: dict[str, Any]
    portfolio_context: ResearchMeetingContext
    error_message: str | None = None


@dataclass
class PortfolioCommitteeOrchestrator:
    """Run the advisory portfolio committee through the shared agent runtime."""

    agent_runtime: AgentRuntime
    portfolio_context_provider: PortfolioContextProvider
    memory_service: Any | None = None
    agents: tuple[CommitteeAgent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.agents:
            self.agents = tuple(
                PromptBackedCommitteeAgent(
                    name=profile.name,
                    role=profile.role.value,
                    prompt_filename=Path(profile.prompt_source).name,
                    agent_id=profile.agent_id,
                    profile=profile,
                )
                for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES
            )

        runtime_memory_service = getattr(self.agent_runtime, "memory_service", None)
        if self.memory_service is None:
            self.memory_service = runtime_memory_service
        elif runtime_memory_service is None and hasattr(
            self.agent_runtime,
            "memory_service",
        ):
            self.agent_runtime.memory_service = self.memory_service

        self._register_portfolio_profiles()

    def run(
        self,
        question: str = "Review the current portfolio.",
        *,
        ticker: str = "PORTFOLIO",
        meeting_id: int = 0,
    ) -> PortfolioCommitteeResult:
        """Build portfolio context, run agents, and return advisory results."""
        context_request = ContextRequest(
            question=question,
            symbols=(ticker,),
            include_portfolio=True,
        )
        portfolio_context = self._build_portfolio_context(context_request)

        agent_results: list[AgentResult] = []
        for agent in self.agents:
            meeting_context = MeetingContext(
                meeting_id=meeting_id,
                question=question,
                ticker=ticker,
                research_context=portfolio_context,
                previous_agent_results=tuple(agent_results),
            )
            agent_results.append(self.agent_runtime.run(agent, meeting_context))

        return PortfolioCommitteeResult(
            status=MeetingStatus.COMPLETED,
            question=question,
            ticker=ticker,
            agent_results=tuple(agent_results),
            metadata=self._metadata(),
            portfolio_context=portfolio_context,
        )

    def _build_portfolio_context(
        self,
        request: ContextRequest,
    ) -> ResearchMeetingContext:
        provider_result = self.portfolio_context_provider.build_context(request)
        if isinstance(provider_result, ContextProviderResult):
            return provider_result.partial_context
        if isinstance(provider_result, ResearchMeetingContext):
            return provider_result
        raise TypeError(
            "portfolio_context_provider.build_context must return "
            "ContextProviderResult or MeetingContext"
        )

    def _register_portfolio_profiles(self) -> None:
        prompt_renderer = getattr(self.agent_runtime, "prompt_renderer", None)
        agent_registry = getattr(prompt_renderer, "agent_registry", None)
        if agent_registry is None:
            return

        for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES:
            exists = getattr(agent_registry, "exists", None)
            if callable(exists) and exists(profile.agent_id):
                continue
            register = getattr(agent_registry, "register", None)
            if callable(register):
                register(profile)

    def _metadata(self) -> dict[str, Any]:
        return {
            "committee": "portfolio",
            "mode": "advisory_analytical",
            "generated_at": datetime.now(UTC).isoformat(),
            "agent_ids": [agent.agent_id for agent in self.agents],
            "agent_names": [agent.name for agent in self.agents],
            "non_execution": True,
        }


__all__ = ["PortfolioCommitteeOrchestrator", "PortfolioCommitteeResult"]
