"""Persistent AI committee meeting orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from parakeetnest.committee.base import CommitteeAgent
from parakeetnest.committee.models import (
    AgentResult,
    InvestmentCommitteeRequest,
    MeetingContext,
    MeetingResult,
    MeetingStatus,
)
from parakeetnest.committee.runtime import AgentRuntime
from parakeetnest.context.models import MeetingContext as ResearchMeetingContext
from parakeetnest.database.repository import CommitteeMeetingRepository
from parakeetnest.logging import get_logger

if TYPE_CHECKING:
    from parakeetnest.committee.memory import CommitteeMemoryService


logger = get_logger(__name__)


@dataclass
class CommitteeMeetingOrchestrator:
    """Run the fixed agent flow for an existing persistent meeting."""

    repository: CommitteeMeetingRepository
    agents: tuple[CommitteeAgent, ...]
    agent_runtime: AgentRuntime | None = None
    memory_service: "CommitteeMemoryService | None" = None
    _memory_writeback_meeting_ids: set[int] = field(
        default_factory=set,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.memory_service is None and self.agent_runtime is not None:
            self.memory_service = self.agent_runtime.memory_service

    def run(
        self,
        meeting_id: int,
        question: str,
        ticker: str,
        research_context: ResearchMeetingContext,
        rendered_investment_intelligence_context: str | None = None,
        investment_committee_request: InvestmentCommitteeRequest | None = None,
    ) -> MeetingResult:
        """Run agents for an existing meeting and persist their messages."""
        agent_results: list[AgentResult] = []
        for agent in self.agents:
            context = MeetingContext(
                meeting_id=meeting_id,
                question=question,
                ticker=ticker,
                research_context=research_context,
                rendered_investment_intelligence_context=(
                    rendered_investment_intelligence_context
                ),
                investment_committee_request=investment_committee_request,
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
        meeting_result = MeetingResult(
            meeting_id=meeting_id,
            status=MeetingStatus.COMPLETED,
            question=question,
            ticker=ticker,
            agent_results=tuple(agent_results),
            result_json=result_json,
        )
        self._write_back_memory(meeting_result)
        return meeting_result

    def _run_agent(self, agent: CommitteeAgent, context: MeetingContext) -> AgentResult:
        """Run a prompt-backed agent, allowing explicit test doubles to fail directly."""
        if self.agent_runtime is not None:
            return self.agent_runtime.run(agent, context)
        legacy_run = getattr(agent, "run", None)
        if callable(legacy_run):
            return legacy_run(context)
        raise TypeError("CommitteeMeetingOrchestrator requires an AgentRuntime")

    def _write_back_memory(self, result: MeetingResult) -> None:
        """Persist useful meeting memories after agent execution completes."""
        if self.memory_service is None:
            return
        if result.meeting_id in self._memory_writeback_meeting_ids:
            return

        try:
            meeting_id = str(result.meeting_id)
            summary = _meeting_summary_content(result)
            if summary is not None:
                self.memory_service.save_meeting_summary(
                    meeting_id=meeting_id,
                    content=summary,
                    metadata={"source": "committee_runtime"},
                )

            decision = _decision_content(result)
            if decision is not None:
                self.memory_service.save_decision(
                    meeting_id=meeting_id,
                    content=decision,
                )

            for agent_result in result.agent_results:
                if agent_result.agent_id and agent_result.ticker:
                    self.memory_service.save_agent_observation(
                        meeting_id=meeting_id,
                        agent_id=agent_result.agent_id,
                        ticker=agent_result.ticker,
                        content=agent_result.content,
                    )
        except Exception as exc:
            logger.warning(
                "Committee memory write-back failed",
                extra={
                    "meeting_id": result.meeting_id,
                    "error_message": str(exc),
                },
            )
            return

        self._memory_writeback_meeting_ids.add(result.meeting_id)


def _meeting_summary_content(result: MeetingResult) -> str | None:
    payload = result.result_json or {}
    for key in ("summary", "rationale", "conclusion"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    return None


def _decision_content(result: MeetingResult) -> str | None:
    payload = result.result_json or {}
    decision_payload = {
        key: payload[key]
        for key in ("action", "decision", "confidence", "horizon", "rationale")
        if key in payload and str(payload[key]).strip()
    }
    if not any(key in decision_payload for key in ("action", "decision")):
        return None
    return json.dumps(decision_payload, sort_keys=True)
