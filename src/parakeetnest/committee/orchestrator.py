"""Persistent AI committee meeting orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass

from parakeetnest.committee.agents import (
    BearAnalystAgent,
    BullAnalystAgent,
    ChairpersonAgent,
    RiskManagerAgent,
)
from parakeetnest.committee.base import CommitteeAgent
from parakeetnest.committee.models import AgentResult, MeetingContext, MeetingResult, MeetingStatus
from parakeetnest.database.repository import CommitteeMeetingRepository
from parakeetnest.llm import LLMProvider


@dataclass
class CommitteeMeetingOrchestrator:
    """Run and persist the first end-to-end AI committee meeting."""

    repository: CommitteeMeetingRepository
    agents: tuple[CommitteeAgent, ...]

    @classmethod
    def default(
        cls,
        repository: CommitteeMeetingRepository,
        llm_provider: LLMProvider,
        model: str = "mock-committee",
    ) -> "CommitteeMeetingOrchestrator":
        """Create the fixed four-agent committee meeting flow."""
        return cls(
            repository=repository,
            agents=(
                BullAnalystAgent(llm_provider, model=model),
                BearAnalystAgent(llm_provider, model=model),
                RiskManagerAgent(llm_provider, model=model),
                ChairpersonAgent(llm_provider, model=model),
            ),
        )

    def run(self, question: str, ticker: str) -> MeetingResult:
        """Create, run, and persist a committee meeting."""
        meeting = self.repository.create_meeting(question=question, ticker=ticker)
        agent_results: list[AgentResult] = []
        try:
            for agent in self.agents:
                context = MeetingContext(
                    meeting_id=meeting.id,
                    question=question,
                    ticker=ticker,
                    previous_agent_results=tuple(agent_results),
                )
                result = agent.run(context)
                self.repository.insert_meeting_message(
                    meeting_id=meeting.id,
                    agent_name=result.agent_name,
                    role=result.role,
                    content=result.content,
                )
                agent_results.append(result)

            final_result = agent_results[-1]
            result_json = json.loads(final_result.content)
            self.repository.update_meeting_completed(meeting.id, result_json)
            return MeetingResult(
                meeting_id=meeting.id,
                status=MeetingStatus.COMPLETED,
                question=question,
                ticker=ticker,
                agent_results=tuple(agent_results),
                result_json=result_json,
            )
        except Exception as exc:
            self.repository.update_meeting_failed(meeting.id, str(exc))
            return MeetingResult(
                meeting_id=meeting.id,
                status=MeetingStatus.FAILED,
                question=question,
                ticker=ticker,
                agent_results=tuple(agent_results),
                error_message=str(exc),
            )
