"""Application service for running committee meetings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from parakeetnest.committee.models import MeetingResult, MeetingStatus
from parakeetnest.context.models import ContextRequest
from parakeetnest.database.repository import CommitteeMeetingRepository
from parakeetnest.logging import get_logger


if TYPE_CHECKING:
    from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
    from parakeetnest.context.service import ContextService


logger = get_logger(__name__)


@dataclass
class MeetingService:
    """Single application entry point for running committee meetings."""

    repository: CommitteeMeetingRepository
    orchestrator: "CommitteeMeetingOrchestrator"
    context_service: "ContextService"

    def run(self, question: str, ticker: str) -> MeetingResult:
        """Create, run, finalize, and return one committee meeting."""
        meeting = self.repository.create_meeting(question=question, ticker=ticker)
        log_context = {
            "meeting_id": meeting.id,
            "ticker": ticker,
            "question": question,
        }
        logger.info("Meeting started", extra=log_context)

        try:
            context_request = ContextRequest(
                question=question,
                symbols=(ticker,),
            )
            meeting_context = self.context_service.build_context(context_request)
            result = self.orchestrator.run(
                meeting_id=meeting.id,
                question=question,
                ticker=ticker,
                research_context=meeting_context,
            )
            result_json = result.result_json or {}
            self.repository.update_meeting_completed(meeting.id, result_json)
            logger.info(
                "Meeting completed",
                extra={
                    **log_context,
                    "status": MeetingStatus.COMPLETED.value,
                },
            )
            return MeetingResult(
                meeting_id=meeting.id,
                status=MeetingStatus.COMPLETED,
                question=question,
                ticker=ticker,
                agent_results=result.agent_results,
                result_json=result_json,
            )
        except Exception as exc:
            self.repository.update_meeting_failed(meeting.id, str(exc))
            logger.exception(
                "Meeting failed",
                extra={
                    **log_context,
                    "status": MeetingStatus.FAILED.value,
                    "error_message": str(exc),
                },
            )
            raise
