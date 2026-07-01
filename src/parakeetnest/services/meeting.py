"""Application service for running committee meetings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING
from typing import Any, Mapping, Protocol

from parakeetnest.committee.models import MeetingResult, MeetingStatus
from parakeetnest.context.models import ContextRequest
from parakeetnest.database.repository import CommitteeMeetingRepository
from parakeetnest.intelligence.context import InvestmentIntelligenceRenderer
from parakeetnest.intelligence.context.models import InvestmentIntelligenceContext
from parakeetnest.logging import get_logger


if TYPE_CHECKING:
    from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
    from parakeetnest.context.service import ContextService


logger = get_logger(__name__)


class InvestmentIntelligenceContextService(Protocol):
    """Service contract for prompt-ready investment intelligence assembly."""

    def build_context(
        self,
        *,
        as_of_date: date | None = None,
        universe: str = "US",
        symbol: str = "SPY",
        health_metadata: Mapping[str, Any] | None = None,
    ) -> InvestmentIntelligenceContext:
        """Return provider-neutral investment intelligence context."""


@dataclass
class MeetingService:
    """Single application entry point for running committee meetings."""

    repository: CommitteeMeetingRepository
    orchestrator: "CommitteeMeetingOrchestrator"
    context_service: "ContextService"
    investment_intelligence_context_service: (
        InvestmentIntelligenceContextService | None
    ) = None
    investment_intelligence_renderer: InvestmentIntelligenceRenderer = field(
        default_factory=InvestmentIntelligenceRenderer
    )

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
            rendered_investment_intelligence_context = (
                self._build_investment_intelligence_context(
                    context_request,
                    ticker=ticker,
                    meeting_id=meeting.id,
                )
            )
            result = self.orchestrator.run(
                meeting_id=meeting.id,
                question=question,
                ticker=ticker,
                research_context=meeting_context,
                rendered_investment_intelligence_context=(
                    rendered_investment_intelligence_context
                ),
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

    def _build_investment_intelligence_context(
        self,
        request: ContextRequest,
        *,
        ticker: str,
        meeting_id: int,
    ) -> str | None:
        """Build and render optional investment intelligence before agents run."""
        if self.investment_intelligence_context_service is None:
            return None

        as_of_date = request.as_of.date() if request.as_of is not None else None
        context = self.investment_intelligence_context_service.build_context(
            as_of_date=as_of_date,
            universe="US",
            symbol=ticker,
            health_metadata={"meeting_id": str(meeting_id)},
        )
        return self.investment_intelligence_renderer.render(context)
