"""Provider-neutral persona-driven committee prompt models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from parakeetnest.committee.playbook_loader import PlaybookLoader
from parakeetnest.committee.personas import (
    DONGDONG_PERSONA,
    XIXI_PERSONA,
    YOUYOU_PERSONA,
    CommitteePersona,
)
from parakeetnest.models import PositionContext, PositionRecommendation
from parakeetnest.portfolio.privacy import (
    PortfolioPositionContext,
    PortfolioSummary,
)


ADVISORY_ONLY_DISCLAIMER = (
    "This is advisory investment research only. Do not provide trading "
    "implementation steps, external account integration steps, or autonomous "
    "investment decisions. A human investor makes the final decision."
)


def _configured_report_language() -> object:
    from parakeetnest.research.localization import get_configured_report_language

    return get_configured_report_language()


def _report_language(value: object) -> object:
    from parakeetnest.research.localization import ReportLanguage

    return ReportLanguage.from_value(value)


def _report_localization(value: object) -> Any:
    from parakeetnest.research.localization import get_report_localization

    return get_report_localization(value)


@dataclass(frozen=True)
class CommitteePromptContext:
    """Report context used to generate one persona-specific reasoning prompt."""

    persona: CommitteePersona
    tickers: tuple[str, ...]
    market_summary: str
    portfolio_review: str
    watchlist_review: str
    ticker_summaries: tuple[str, ...]
    evidence_notes: tuple[str, ...]
    key_risks: tuple[str, ...]
    upcoming_catalysts: tuple[str, ...]
    portfolio_summary: PortfolioSummary | None = None
    position_context: PortfolioPositionContext | None = None
    public_market_facts: tuple[str, ...] = field(default_factory=tuple)
    company_facts: tuple[str, ...] = field(default_factory=tuple)
    macro_facts: tuple[str, ...] = field(default_factory=tuple)
    advisory_only_disclaimer: str = ADVISORY_ONLY_DISCLAIMER
    report_language: object | str = field(default_factory=_configured_report_language)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tickers", _normalize_text_tuple(self.tickers))
        object.__setattr__(
            self,
            "market_summary",
            _required_text(self.market_summary, "market_summary"),
        )
        object.__setattr__(
            self,
            "portfolio_review",
            _required_text(self.portfolio_review, "portfolio_review"),
        )
        object.__setattr__(
            self,
            "watchlist_review",
            _required_text(self.watchlist_review, "watchlist_review"),
        )
        object.__setattr__(
            self,
            "ticker_summaries",
            _normalize_text_tuple(self.ticker_summaries),
        )
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )
        object.__setattr__(
            self,
            "key_risks",
            _normalize_text_tuple(self.key_risks),
        )
        object.__setattr__(
            self,
            "upcoming_catalysts",
            _normalize_text_tuple(self.upcoming_catalysts),
        )
        object.__setattr__(
            self,
            "public_market_facts",
            _normalize_text_tuple(self.public_market_facts),
        )
        object.__setattr__(
            self,
            "company_facts",
            _normalize_text_tuple(self.company_facts),
        )
        object.__setattr__(
            self,
            "macro_facts",
            _normalize_text_tuple(self.macro_facts),
        )
        object.__setattr__(
            self,
            "advisory_only_disclaimer",
            _required_text(
                self.advisory_only_disclaimer,
                "advisory_only_disclaimer",
            ),
        )
        object.__setattr__(
            self,
            "report_language",
            _report_language(self.report_language),
        )
        if not self.tickers:
            raise ValueError("prompt context tickers are required")


@dataclass(frozen=True)
class CommitteePersonaPrompt:
    """Generated prompt artifact for one committee persona."""

    persona_id: str
    display_name: str
    role_title: str
    prompt_text: str
    context: CommitteePromptContext = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "persona_id",
            _required_text(self.persona_id, "persona_id"),
        )
        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name"),
        )
        object.__setattr__(
            self,
            "role_title",
            _required_text(self.role_title, "role_title"),
        )
        object.__setattr__(
            self,
            "prompt_text",
            _required_text(self.prompt_text, "prompt_text"),
        )


@dataclass(frozen=True)
class PositionReviewPrompt:
    """Generated prompt artifact for one position-level committee review."""

    persona_id: str
    display_name: str
    role_title: str
    prompt_text: str
    context: PositionContext = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "persona_id",
            _required_text(self.persona_id, "persona_id"),
        )
        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name"),
        )
        object.__setattr__(
            self,
            "role_title",
            _required_text(self.role_title, "role_title"),
        )
        object.__setattr__(
            self,
            "prompt_text",
            _required_text(self.prompt_text, "prompt_text"),
        )


class CommitteePromptBuilder(Protocol):
    """Provider-neutral contract for persona-driven committee prompt builders."""

    def build_prompts(
        self,
        contexts: tuple[CommitteePromptContext, ...],
    ) -> tuple[CommitteePersonaPrompt, ...]:
        """Build persona prompts in committee order."""


class PersonaDrivenCommitteePromptBuilder:
    """Build deterministic prompt text from stable committee persona fields."""

    def __init__(self, playbook_loader: PlaybookLoader | None = None) -> None:
        self._playbook_loader = playbook_loader or PlaybookLoader()
        self._playbook_loader.validate_required_files()

    def build_prompts(
        self,
        contexts: tuple[CommitteePromptContext, ...],
    ) -> tuple[CommitteePersonaPrompt, ...]:
        """Build one prompt per supplied committee prompt context."""
        return tuple(self.build_prompt(context) for context in contexts)

    def build_prompt(self, context: CommitteePromptContext) -> CommitteePersonaPrompt:
        """Build a prompt for one permanent committee persona."""
        persona = context.persona
        localization = _report_localization(context.report_language)
        persona_playbook = self._playbook_loader.load_persona_playbook(persona.id)
        prompt_text = "\n".join(
            [
                "System Playbook",
                self._playbook_loader.load_system_playbook(),
                "",
                "Common Committee Rules",
                self._playbook_loader.load_common_playbook(),
                "",
                "Persona Playbook",
                persona_playbook,
                "",
                f"You are {persona.display_name}, {persona.role_title}.",
                "",
                "Persona",
                f"- Responsibility: {persona.responsibility}",
                f"- Default viewpoint: {persona.default_viewpoint}",
                f"- Risk posture: {persona.risk_posture}",
                f"- Writing style: {persona.writing_style.value}",
                "- Evidence requirements:",
                *_render_items(persona.evidence_requirements),
                "- Decision biases to avoid:",
                *_render_items(persona.decision_biases_to_avoid),
                "",
                "Report Context",
                f"- Tickers: {', '.join(context.tickers)}",
                f"- Market summary: {context.market_summary}",
                f"- Portfolio review: {context.portfolio_review}",
                f"- Watchlist review: {context.watchlist_review}",
                "- Ticker summaries:",
                *_render_items(context.ticker_summaries),
                "- Evidence notes:",
                *_render_items(context.evidence_notes),
                "- Key risks:",
                *_render_items(context.key_risks),
                "- Upcoming catalysts:",
                *_render_items(context.upcoming_catalysts),
                "",
                "PUBLIC FACTS",
                "- Yahoo / market data facts:",
                *_render_items(context.public_market_facts),
                "- SEC EDGAR facts:",
                *_render_items(context.company_facts),
                "- FRED macro facts:",
                *_render_items(context.macro_facts),
                "",
                "PRIVATE PORTFOLIO CONTEXT, BUCKETED",
                *_render_portfolio_summary(context.portfolio_summary),
                *_render_position_context(context.position_context),
                "",
                "Advisory Boundary",
                f"- {context.advisory_only_disclaimer}",
                "",
                "Language",
                f"- {localization.language_instruction}",
                "",
                "Required Output",
                "- Provide a concise committee opinion for the daily report.",
                "- Include action, confidence, horizon, evidence, risks, and catalysts.",
                "- Ground the reasoning in the supplied context and persona viewpoint.",
                "- Do not include trading implementation or autonomous decisioning.",
            ]
        )
        return CommitteePersonaPrompt(
            persona_id=persona.id,
            display_name=persona.display_name,
            role_title=persona.role_title,
            prompt_text=prompt_text,
            context=context,
        )


class PositionReviewPromptBuilder(Protocol):
    """Provider-neutral contract for position-level committee review prompts."""

    def build_prompts(
        self,
        context: PositionContext,
    ) -> tuple[PositionReviewPrompt, ...]:
        """Build all position review prompts in committee review order."""


class PersonaDrivenPositionReviewPromptBuilder:
    """Build deterministic position-review prompts from committee personas."""

    def __init__(
        self,
        language: str | None = None,
        localization: Any | None = None,
    ) -> None:
        self._localization = localization or _report_localization(language)

    def build_prompts(
        self,
        context: PositionContext,
    ) -> tuple[PositionReviewPrompt, ...]:
        """Build Dongdong, Xixi, and Youyou prompts for one position."""
        return (
            self.build_dongdong_prompt(context),
            self.build_xixi_prompt(context),
            self.build_youyou_prompt(context),
        )

    def build_dongdong_prompt(self, context: PositionContext) -> PositionReviewPrompt:
        """Build Dongdong's opportunity-focused position review prompt."""
        return self.build_prompt(
            context,
            DONGDONG_PERSONA,
            "Focus on opportunity, growth, upside, positive inflections, and catalysts.",
        )

    def build_xixi_prompt(self, context: PositionContext) -> PositionReviewPrompt:
        """Build Xixi's fundamentals-focused position review prompt."""
        return self.build_prompt(
            context,
            XIXI_PERSONA,
            "Focus on fundamentals, valuation, business quality, durability, and execution.",
        )

    def build_youyou_prompt(self, context: PositionContext) -> PositionReviewPrompt:
        """Build Youyou's risk-focused position review prompt."""
        return self.build_prompt(
            context,
            YOUYOU_PERSONA,
            "Focus on risk, downside, concentration, uncertainty, and missing evidence.",
        )

    def build_prompt(
        self,
        context: PositionContext,
        persona: CommitteePersona,
        position_review_lens: str,
    ) -> PositionReviewPrompt:
        """Build a prompt for one committee member's review of a current position."""
        prompt_text = "\n".join(
            [
                f"You are {persona.display_name}, {persona.role_title}.",
                "",
                "Position Review Lens",
                f"- {position_review_lens}",
                f"- Responsibility: {persona.responsibility}",
                f"- Default viewpoint: {persona.default_viewpoint}",
                f"- Risk posture: {persona.risk_posture}",
                "- Evidence requirements:",
                *_render_items(persona.evidence_requirements),
                "",
                "Position Context",
                f"- Symbol: {context.symbol}",
                f"- Company name: {context.company_name}",
                f"- Current price: {_format_optional_number(context.current_price)}",
                (
                    "- Recent price change: "
                    f"{_format_optional_number(context.recent_price_change)}"
                ),
                "- Relevant news:",
                *_render_items(context.relevant_news),
                "- Relevant research:",
                *_render_items(context.relevant_research),
                "- Risk notes:",
                *_render_items(context.risk_notes),
                "- Valuation notes:",
                *_render_items(context.valuation_notes),
                "- Momentum notes:",
                *_render_items(context.momentum_notes),
                "- Portfolio notes:",
                *_render_items(context.portfolio_notes),
                "",
                "Required Output",
                "- Return only a JSON object named CommitteePositionReview.",
                f"- {self._localization.position_language_instruction}",
                "- Include exactly these fields:",
                "  - symbol",
                "  - agent_name",
                "  - thesis",
                "  - concerns",
                "  - recommendation",
                "  - confidence",
                "  - evidence_refs",
                (
                    "- recommendation must be one of: "
                    f"{', '.join(item.value for item in PositionRecommendation)}."
                ),
                "- confidence must be one of: high, medium, low.",
                "- evidence_refs must cite supplied context labels or facts.",
                "- Do not generate PositionDecision or a final Chairman decision.",
                "- Do not include trading implementation or autonomous decisioning.",
            ]
        )
        return PositionReviewPrompt(
            persona_id=persona.id,
            display_name=persona.display_name,
            role_title=persona.role_title,
            prompt_text=prompt_text,
            context=context,
        )


def _render_items(values: tuple[str, ...]) -> list[str]:
    normalized = _normalize_text_tuple(values)
    if not normalized:
        return ["  - None supplied."]
    return [f"  - {value}" for value in normalized]


def _render_portfolio_summary(summary: PortfolioSummary | None) -> list[str]:
    if summary is None:
        return ["- Portfolio summary: None supplied."]
    return [
        f"- Portfolio privacy level: {summary.privacy_level}",
        f"- Number of positions: {summary.number_of_positions}",
        f"- Cash allocation bucket: {summary.cash_allocation_bucket}",
        f"- Concentration level: {summary.concentration_level}",
        f"- Largest position bucket: {summary.largest_position_bucket}",
        f"- Top 5 concentration bucket: {summary.top5_concentration_bucket}",
        f"- Dominant sector: {summary.dominant_sector or 'unknown'}",
        f"- Style exposure: {summary.style_exposure}",
    ]


def _render_position_context(
    context: PortfolioPositionContext | None,
) -> list[str]:
    if context is None:
        return ["- Position context: None supplied."]
    return [
        f"- Ticker: {context.ticker}",
        f"- Privacy level: {context.privacy_level}",
        f"- Is holding: {context.is_holding}",
        f"- Position size bucket: {context.position_size_bucket}",
        f"- Portfolio rank bucket: {context.portfolio_rank_bucket}",
        f"- Unrealized return bucket: {context.unrealized_return_bucket}",
        f"- Holding role: {context.holding_role}",
        f"- Add allowed: {context.add_allowed}",
        f"- Trim candidate: {context.trim_candidate}",
    ]


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "None supplied"
    return f"{value:g}"


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_text_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


__all__ = [
    "ADVISORY_ONLY_DISCLAIMER",
    "CommitteePersonaPrompt",
    "CommitteePromptBuilder",
    "CommitteePromptContext",
    "PersonaDrivenPositionReviewPromptBuilder",
    "PersonaDrivenCommitteePromptBuilder",
    "PositionReviewPrompt",
    "PositionReviewPromptBuilder",
]
