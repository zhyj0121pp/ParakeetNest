"""Persistent AI committee meeting orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass

from parakeetnest.committee.base import CommitteeAgent
from parakeetnest.committee.models import AgentResult, MeetingContext, MeetingResult, MeetingStatus
from parakeetnest.committee.runtime import AgentRuntime
from parakeetnest.context.models import MeetingContext as ResearchMeetingContext
from parakeetnest.database.repository import CommitteeMeetingRepository


@dataclass
class CommitteeMeetingOrchestrator:
    """Run the fixed agent flow for an existing persistent meeting."""

    repository: CommitteeMeetingRepository
    agents: tuple[CommitteeAgent, ...]
    agent_runtime: AgentRuntime | None = None

    def run(
        self,
        meeting_id: int,
        question: str,
        ticker: str,
        research_context: ResearchMeetingContext,
    ) -> MeetingResult:
        """Run agents for an existing meeting and persist their messages."""
        agent_results: list[AgentResult] = []
        for agent in self.agents:
            context = MeetingContext(
                meeting_id=meeting_id,
                question=question,
                ticker=ticker,
                research_context=research_context,
                previous_agent_results=tuple(agent_results),
            )
            result = self._run_agent(agent, context)
            self.repository.insert_meeting_message(
                meeting_id=meeting_id,
                agent_name=result.agent_name,
                role=result.role,
                content=result.content,
            )
            agent_results.append(result)

        final_result = agent_results[-1]
        result_json = json.loads(final_result.content)
        return MeetingResult(
            meeting_id=meeting_id,
            status=MeetingStatus.COMPLETED,
            question=question,
            ticker=ticker,
            agent_results=tuple(agent_results),
            result_json=result_json,
        )

    def _run_agent(self, agent: CommitteeAgent, context: MeetingContext) -> AgentResult:
        """Run a prompt-backed agent, allowing explicit test doubles to fail directly."""
        if self.agent_runtime is not None:
            return self.agent_runtime.run(agent, context)
        legacy_run = getattr(agent, "run", None)
        if callable(legacy_run):
            return legacy_run(context)
        raise TypeError("CommitteeMeetingOrchestrator requires an AgentRuntime")
