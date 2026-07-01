"""Application service for running committee meetings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
from typing import TYPE_CHECKING
from typing import Any, Mapping, Protocol

from parakeetnest.committee.models import (
    AgentResult,
    InvestmentCommitteeDecision,
    InvestmentCommitteeReport,
    InvestmentCommitteeRequest,
    MeetingResult,
    MeetingStatus,
)
from parakeetnest.context.models import ContextRequest
from parakeetnest.database.repository import CommitteeMeetingRepository
from parakeetnest.intelligence.context import InvestmentIntelligenceRenderer
from parakeetnest.intelligence.context.models import InvestmentIntelligenceContext
from parakeetnest.logging import get_logger
from parakeetnest.models import ConfidenceLevel


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

    def execute_investment_committee(
        self,
        request: InvestmentCommitteeRequest,
    ) -> InvestmentCommitteeReport:
        """Run one complete investment committee request and return its report."""
        question = self._question_from_investment_committee_request(request)
        meeting = self.repository.create_meeting(
            question=question,
            ticker=request.ticker,
        )
        log_context = {
            "meeting_id": meeting.id,
            "ticker": request.ticker,
            "topic": request.topic,
        }
        logger.info("Investment committee meeting started", extra=log_context)

        try:
            context_request = ContextRequest(
                question=question,
                symbols=(request.ticker,),
            )
            meeting_context = self.context_service.build_context(context_request)
            rendered_investment_intelligence_context = (
                self._build_investment_intelligence_context(
                    context_request,
                    ticker=request.ticker,
                    meeting_id=meeting.id,
                )
            )
            result = self.orchestrator.run(
                meeting_id=meeting.id,
                question=question,
                ticker=request.ticker,
                research_context=meeting_context,
                rendered_investment_intelligence_context=(
                    rendered_investment_intelligence_context
                ),
                investment_committee_request=request,
            )
            report = self._build_investment_committee_report(
                request=request,
                result=result,
                rendered_investment_intelligence_context=(
                    rendered_investment_intelligence_context
                ),
            )
            self.repository.update_meeting_completed(
                meeting.id,
                self._report_to_json(report),
            )
            logger.info(
                "Investment committee meeting completed",
                extra={
                    **log_context,
                    "status": MeetingStatus.COMPLETED.value,
                },
            )
            return report
        except Exception as exc:
            self.repository.update_meeting_failed(meeting.id, str(exc))
            logger.exception(
                "Investment committee meeting failed",
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

    @staticmethod
    def _question_from_investment_committee_request(
        request: InvestmentCommitteeRequest,
    ) -> str:
        question = request.user_question or request.topic
        parts = [
            question,
            f"Topic: {request.topic}.",
            f"Time horizon: {request.time_horizon.value}.",
        ]
        if request.portfolio_context_notes:
            parts.append(f"Portfolio context: {request.portfolio_context_notes}.")
        return " ".join(part for part in parts if part)

    def _build_investment_committee_report(
        self,
        *,
        request: InvestmentCommitteeRequest,
        result: MeetingResult,
        rendered_investment_intelligence_context: str | None,
    ) -> InvestmentCommitteeReport:
        payloads = self._agent_payloads(result.agent_results)
        chairman_payload = result.result_json or {}
        risks = self._collect_list_values(payloads, "risks")
        if not risks:
            risks = ("No key risks were generated by the committee.",)

        return InvestmentCommitteeReport(
            ticker=request.ticker,
            topic=request.topic,
            time_horizon=request.time_horizon,
            macro_view=self._extract_markdown_section(
                rendered_investment_intelligence_context,
                "Economic Regime",
            ),
            sector_view=self._extract_markdown_section(
                rendered_investment_intelligence_context,
                "Sector Rotation",
            ),
            fundamental_view=self._viewpoint_for_agent(
                payloads,
                "Xixi",
                "No fundamental view was generated by the committee.",
            ),
            valuation_view=str(
                chairman_payload.get(
                    "rationale",
                    "No valuation-specific view was generated by the committee.",
                )
            ),
            risk_view=self._viewpoint_for_agent(
                payloads,
                "Yoyo",
                self._extract_markdown_section(
                    rendered_investment_intelligence_context,
                    "Risk",
                ),
            ),
            momentum_sentiment_view="\n\n".join(
                section
                for section in (
                    self._extract_markdown_section(
                        rendered_investment_intelligence_context,
                        "Momentum",
                    ),
                    self._extract_markdown_section(
                        rendered_investment_intelligence_context,
                        "Market Sentiment",
                    ),
                )
                if section
            )
            or "No momentum or sentiment view was generated by the committee.",
            bull_case=self._viewpoint_for_agent(
                payloads,
                "Dongdong",
                "No bull case was generated by the committee.",
            ),
            bear_case="; ".join(risks),
            key_risks=risks,
            decision=self._decision_from_action(chairman_payload.get("action")),
            confidence=chairman_payload.get("confidence", ConfidenceLevel.LOW.value),
            recommended_action=self._recommended_action(chairman_payload),
        )

    @staticmethod
    def _agent_payloads(agent_results: tuple[AgentResult, ...]) -> dict[str, dict[str, Any]]:
        payloads: dict[str, dict[str, Any]] = {}
        for result in agent_results:
            try:
                payload = json.loads(result.content)
            except json.JSONDecodeError:
                payload = {"viewpoint": result.content}
            if isinstance(payload, dict):
                payloads[result.agent_name.lower()] = payload
        return payloads

    @staticmethod
    def _collect_list_values(
        payloads: dict[str, dict[str, Any]],
        key: str,
    ) -> tuple[str, ...]:
        values: list[str] = []
        for payload in payloads.values():
            raw_values = payload.get(key, ())
            if not isinstance(raw_values, list):
                continue
            for value in raw_values:
                normalized = str(value).strip()
                if normalized and normalized not in values:
                    values.append(normalized)
        return tuple(values)

    @staticmethod
    def _viewpoint_for_agent(
        payloads: dict[str, dict[str, Any]],
        agent_name: str,
        fallback: str,
    ) -> str:
        payload = payloads.get(agent_name.lower(), {})
        viewpoint = str(payload.get("viewpoint", "")).strip()
        return viewpoint or fallback

    @staticmethod
    def _extract_markdown_section(markdown: str | None, heading: str) -> str:
        if not markdown:
            return f"No {heading.lower()} context available."

        section_heading = f"## {heading}"
        lines = markdown.splitlines()
        try:
            start_index = lines.index(section_heading)
        except ValueError:
            return f"No {heading.lower()} context available."

        section_lines: list[str] = []
        for line in lines[start_index + 1 :]:
            if line.startswith("## "):
                break
            section_lines.append(line)
        rendered = "\n".join(line for line in section_lines).strip()
        return rendered or f"No {heading.lower()} context available."

    @staticmethod
    def _decision_from_action(action: object) -> InvestmentCommitteeDecision:
        normalized_action = str(action or "").strip().lower()
        if normalized_action == "buy":
            return InvestmentCommitteeDecision.BUY
        if normalized_action == "hold":
            return InvestmentCommitteeDecision.HOLD
        if normalized_action == "watch":
            return InvestmentCommitteeDecision.WATCH
        return InvestmentCommitteeDecision.AVOID

    @staticmethod
    def _recommended_action(payload: Mapping[str, Any]) -> str:
        action = str(payload.get("action", "watch")).strip().lower() or "watch"
        rationale = str(payload.get("rationale", "")).strip()
        if rationale:
            return f"{action}: {rationale}"
        return action

    @staticmethod
    def _report_to_json(report: InvestmentCommitteeReport) -> dict[str, object]:
        return {
            "ticker": report.ticker,
            "topic": report.topic,
            "time_horizon": report.time_horizon.value,
            "macro_view": report.macro_view,
            "sector_view": report.sector_view,
            "fundamental_view": report.fundamental_view,
            "valuation_view": report.valuation_view,
            "risk_view": report.risk_view,
            "momentum_sentiment_view": report.momentum_sentiment_view,
            "bull_case": report.bull_case,
            "bear_case": report.bear_case,
            "key_risks": list(report.key_risks),
            "decision": report.decision.value,
            "confidence": report.confidence.value,
            "recommended_action": report.recommended_action,
        }
