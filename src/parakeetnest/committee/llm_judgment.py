"""LLM-backed daily report committee judgment with deterministic fallback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from parakeetnest.committee.judgment import CommitteeJudgmentService
from parakeetnest.committee.prompting import CommitteePersonaPrompt
from parakeetnest.llm.models import LLMRequest
from parakeetnest.llm.parser import OutputParser, OutputParserError
from parakeetnest.llm.provider import LLMProvider
from parakeetnest.llm.schemas import CHAIRMAN_SUMMARY_SCHEMA, COMMITTEE_OPINION_SCHEMA

if TYPE_CHECKING:
    from parakeetnest.committee.models import ChairmanSummary, CommitteeOpinion
    from parakeetnest.research.models import (
        ResearchCommitteeConsensus,
        ResearchCommitteeOpinion,
        ResearchPositionDecision,
        ResearchTickerReport,
    )


class LLMCommitteeJudgmentService:
    """Generate daily report opinions through the configured LLM provider."""

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        fallback_service: CommitteeJudgmentService | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        max_completion_tokens: int = 350,
        parser: OutputParser | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._fallback_service = fallback_service or CommitteeJudgmentService()
        self._model = model or getattr(llm_provider, "default_model", "committee-llm")
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds
        self._max_completion_tokens = max_completion_tokens
        self._parser = parser or OutputParser()
        self._last_used_fallback = False

    def build_opinions(
        self,
        committee_prompts: tuple[CommitteePersonaPrompt, ...],
        ticker_reports: tuple[ResearchTickerReport, ...],
    ) -> tuple[ResearchCommitteeOpinion, ...]:
        """Build persona opinions, falling back if any model output is invalid."""
        self._last_used_fallback = False
        try:
            return tuple(
                self._to_research_opinion(
                    prompt,
                    self._run_persona_prompt(prompt, ticker_reports),
                )
                for prompt in committee_prompts
            )
        except (OutputParserError, ValueError, KeyError, TypeError):
            self._last_used_fallback = True
            return self._fallback_service.build_opinions(
                committee_prompts,
                ticker_reports,
            )

    def build_consensus(
        self,
        ticker_reports: tuple[ResearchTickerReport, ...],
        *,
        language: object | None = None,
        committee_opinions: tuple[ResearchCommitteeOpinion, ...] = (),
    ) -> ResearchCommitteeConsensus:
        """Build Chairman synthesis, falling back if model output is invalid."""
        if self._last_used_fallback:
            return self._fallback_service.build_consensus(
                ticker_reports,
                language=language,
            )
        try:
            return self._to_research_consensus(
                self._run_chairman_prompt(
                    ticker_reports,
                    committee_opinions=committee_opinions,
                    language=language,
                )
            )
        except (OutputParserError, ValueError, KeyError, TypeError):
            return self._fallback_service.build_consensus(
                ticker_reports,
                language=language,
            )

    def build_position_review(
        self,
        ticker_report: ResearchTickerReport,
        committee_prompts: tuple[CommitteePersonaPrompt, ...],
        *,
        language: object | None = None,
    ) -> ResearchPositionDecision | None:
        """Build one ticker-level review or return None for deterministic fallback."""
        from parakeetnest.research.models import ResearchPositionDecision

        ticker_reports = (ticker_report,)
        try:
            persona_outputs = self._build_persona_opinions(
                committee_prompts,
                ticker_reports,
            )
            consensus = self._to_research_consensus(
                self._run_chairman_prompt(
                    ticker_reports,
                    committee_opinions=persona_outputs,
                    language=language,
                )
            )
        except (OutputParserError, ValueError, KeyError, TypeError):
            return None

        opinions = tuple(
            self._to_research_opinion(prompt, opinion)
            for prompt, opinion in zip(
                committee_prompts,
                persona_outputs,
                strict=True,
            )
        )
        return ResearchPositionDecision(
            ticker=ticker_report.ticker,
            dongdong_opinion=_opinion_text(opinions, "dongdong"),
            xixi_opinion=_opinion_text(opinions, "xixi"),
            yoyo_opinion=_opinion_text(opinions, "yoyo"),
            consensus=consensus,
            recommendation=consensus.final_action,
            confidence=consensus.confidence,
            rationale=consensus.rationale,
            evidence=_ticker_evidence(ticker_report),
        )

    def _build_persona_opinions(
        self,
        committee_prompts: tuple[CommitteePersonaPrompt, ...],
        ticker_reports: tuple[ResearchTickerReport, ...],
    ) -> tuple[CommitteeOpinion, ...]:
        if not committee_prompts:
            return ()
        max_workers = min(3, len(committee_prompts))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = tuple(
                executor.submit(
                    self._run_persona_prompt,
                    prompt,
                    ticker_reports,
                )
                for prompt in committee_prompts
            )
            return tuple(future.result() for future in futures)

    def _run_persona_prompt(
        self,
        prompt: CommitteePersonaPrompt,
        ticker_reports: tuple[ResearchTickerReport, ...],
    ) -> CommitteeOpinion:
        persona_name = _persona_display_name(prompt)
        request = LLMRequest(
            prompt=_persona_prompt_text(prompt, ticker_reports),
            model=self._model,
            temperature=self._temperature,
            timeout_seconds=self._timeout_seconds,
            max_completion_tokens=self._max_completion_tokens,
            response_schema=COMMITTEE_OPINION_SCHEMA,
            metadata={
                "task": "daily_report_persona_opinion",
                "agent_name": persona_name,
                "role": prompt.role_title,
                "persona_id": prompt.persona_id,
                "tickers": ",".join(report.ticker for report in ticker_reports),
            },
        )
        return self._parser.parse_committee_opinion(self._llm_provider.complete(request))

    def _run_chairman_prompt(
        self,
        ticker_reports: tuple[ResearchTickerReport, ...],
        *,
        committee_opinions: tuple[CommitteeOpinion, ...],
        language: object | None,
    ) -> ChairmanSummary:
        request = LLMRequest(
            prompt=_chairman_prompt_text(
                ticker_reports,
                committee_opinions=committee_opinions,
                language=language,
            ),
            model=self._model,
            temperature=self._temperature,
            timeout_seconds=self._timeout_seconds,
            max_completion_tokens=self._max_completion_tokens,
            response_schema=CHAIRMAN_SUMMARY_SCHEMA,
            metadata={
                "task": "daily_report_chairman_synthesis",
                "agent_name": "Chairman",
                "role": "final decision maker",
                "tickers": ",".join(report.ticker for report in ticker_reports),
            },
        )
        return self._parser.parse_chairman_summary(self._llm_provider.complete(request))

    @staticmethod
    def _to_research_opinion(
        prompt: CommitteePersonaPrompt,
        opinion: CommitteeOpinion,
    ) -> ResearchCommitteeOpinion:
        from parakeetnest.research.models import ResearchCommitteeOpinion

        evidence = tuple(
            f"{item.source}: {item.summary}" for item in opinion.evidence
        ) or ("LLM cited supplied committee prompt context.",)
        risks = tuple(opinion.risks) or ("Risk evidence was limited.",)
        catalysts = tuple(opinion.catalysts) or ("Catalyst evidence was limited.",)
        return ResearchCommitteeOpinion(
            persona_id=prompt.persona_id,
            display_name=_persona_display_name(prompt),
            role_title=prompt.role_title,
            stance=_stance_from_action(opinion.viewpoint),
            reasoning_summary=opinion.viewpoint,
            evidence_considered=evidence,
            key_concern=risks[0],
            suggested_action=_suggested_action(opinion, catalysts),
            responsibility=prompt.context.persona.responsibility,
            viewpoint=prompt.context.persona.default_viewpoint,
            risk_posture=prompt.context.persona.risk_posture,
            evidence_requirements=prompt.context.persona.evidence_requirements,
            writing_style=prompt.context.persona.writing_style.value,
            decision_biases_to_avoid=prompt.context.persona.decision_biases_to_avoid,
        )

    @staticmethod
    def _to_research_consensus(
        summary: ChairmanSummary,
    ) -> ResearchCommitteeConsensus:
        from parakeetnest.research.models import ResearchCommitteeConsensus

        evidence = tuple(f"{item.source}: {item.summary}" for item in summary.evidence)
        actions = (
            f"{summary.symbol}: {summary.action.value} with "
            f"{summary.confidence.value} confidence over {summary.horizon.value}."
        )
        return ResearchCommitteeConsensus(
            final_action=summary.action.value,
            confidence=summary.confidence.value,
            horizon=summary.horizon.value,
            rationale=summary.rationale,
            final_risk_posture="; ".join(summary.risks) or summary.data_confidence.value,
            todays_suggested_actions=(actions,) + evidence[:2],
        )


def _persona_prompt_text(
    prompt: CommitteePersonaPrompt,
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> str:
    return "\n".join(
        [
            prompt.prompt_text,
            "",
            "LLM Grounding Rules",
            "- Use only the supplied source-labeled facts and PRE-COMMITTEE ANALYSIS.",
            "- Treat PRE-COMMITTEE ANALYSIS as deterministic interpretation, separate from factual evidence.",
            "- Do not expose raw provider fields or private account details.",
            "- Do not recommend or describe automatic trading.",
            "- Be concise and explicit; no long-form essay or broad market commentary.",
            "- Discuss only the ticker named in this prompt.",
            "",
            "Required JSON",
            "- Return only a JSON object matching CommitteeOpinion.",
            "- viewpoint must be 2-4 short sentences and include action, confidence, horizon, evidence, risks, and catalysts.",
            "- evidence, risks, and catalysts arrays must each contain at most 2 short items.",
            f"- symbol must be {_symbol_for_reports(ticker_reports)}.",
        ]
    )


def _chairman_prompt_text(
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    committee_opinions: tuple[ResearchCommitteeOpinion, ...],
    language: object | None,
) -> str:
    return "\n".join(
        [
            "You are Chairman, the final advisory decision maker.",
            "Synthesize Dongdong, Xixi, and Yoyo into one advisory recommendation.",
            "",
            "LLM Grounding Rules",
            "- Use only the supplied Dongdong, Xixi, and Yoyo opinions.",
            "- Do not introduce new facts or perform independent company analysis.",
            "- Resolve disagreement by evidence quality, risk asymmetry, and portfolio constraints.",
            "- Do not expose raw provider fields or private account details.",
            "- Do not recommend or describe automatic trading.",
            "- Be concise and explicit; no long-form essay or broad market commentary.",
            "- Discuss only the ticker named in this prompt.",
            "",
            "Ticker",
            f"- {_symbol_for_reports(ticker_reports)}",
            "",
            "Portfolio Constraints",
            *_render_portfolio_constraints(ticker_reports),
            "",
            "Persona Opinions",
            *_render_opinions(committee_opinions),
            "",
            "Language",
            f"- Match report language: {language}.",
            "",
            "Required JSON",
            "- Return only a JSON object matching ChairmanSummary.",
            "- rationale must be 2-3 short sentences.",
            "- Include action, confidence, horizon, evidence, risks, and catalysts.",
            "- evidence, risks, and catalysts arrays must each contain at most 2 short items.",
            f"- symbol must be {_symbol_for_reports(ticker_reports)}.",
        ]
    )


def _render_portfolio_constraints(
    ticker_reports: tuple[ResearchTickerReport, ...],
) -> list[str]:
    values: list[str] = []
    for report in ticker_reports:
        context = report.position_context
        if context is None:
            continue
        values.extend(
            (
                f"- {report.ticker} add_allowed={context.add_allowed}",
                f"- {report.ticker} trim_candidate={context.trim_candidate}",
            )
        )
    return values or ["- None supplied."]


def _render_opinions(
    committee_opinions: tuple[CommitteeOpinion, ...],
) -> list[str]:
    if not committee_opinions:
        return ["- None supplied."]
    return [
        (
            f"- {opinion.member_name} ({opinion.role}): "
            f"viewpoint={_truncate(opinion.viewpoint)}; "
            f"confidence={opinion.confidence.value}; "
            f"evidence={'; '.join(f'{item.source}: {item.summary}' for item in opinion.evidence[:2])}; "
            f"risks={'; '.join(opinion.risks[:2])}; "
            f"catalysts={'; '.join(opinion.catalysts[:2])}"
        )
        for opinion in committee_opinions
    ]


def _truncate(value: str, *, limit: int = 360) -> str:
    stripped = " ".join(value.split())
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[: limit - 3].rstrip()}..."


def _opinion_text(
    opinions: tuple[ResearchCommitteeOpinion, ...],
    persona_id: str,
) -> str:
    for opinion in opinions:
        if opinion.persona_id == persona_id:
            return opinion.reasoning_summary
    return "Committee opinion unavailable."


def _ticker_evidence(report: ResearchTickerReport) -> tuple[str, ...]:
    values = (
        tuple(f"{finding.source}: {finding.summary}" for finding in report.findings)
        + report.public_market_facts
        + report.profile_facts
        + report.valuation_facts
        + report.financial_facts
        + report.news_facts
        + report.company_facts
        + report.macro_facts
        + tuple(f"risk: {risk.summary}" for risk in report.risks)
        + tuple(f"catalyst: {catalyst.summary}" for catalyst in report.catalysts)
    )
    return tuple(value for value in values if value.strip()) or (
        "research_service: connected factual context is limited.",
    )


def _persona_display_name(prompt: CommitteePersonaPrompt) -> str:
    if prompt.persona_id == "yoyo":
        return "Yoyo"
    return prompt.display_name


def _symbol_for_reports(ticker_reports: tuple[ResearchTickerReport, ...]) -> str:
    tickers = tuple(report.ticker for report in ticker_reports)
    if len(tickers) == 1:
        return tickers[0]
    return ",".join(tickers)


def _stance_from_action(text: str) -> str:
    normalized = text.lower()
    if "reduce" in normalized or "sell" in normalized or "risk" in normalized:
        return "cautious"
    if "buy" in normalized:
        return "bullish"
    return "neutral"


def _suggested_action(opinion: CommitteeOpinion, catalysts: tuple[str, ...]) -> str:
    return (
        f"{opinion.symbol}: {opinion.confidence.value} confidence; "
        f"next catalyst to watch: {catalysts[0]}"
    )


__all__ = ["LLMCommitteeJudgmentService"]
