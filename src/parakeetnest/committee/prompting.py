"""Provider-neutral persona-driven committee prompt models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from parakeetnest.committee.personas import (
    DONGDONG_PERSONA,
    XIXI_PERSONA,
    YOUYOU_PERSONA,
    CommitteePersona,
)
from parakeetnest.models import PositionContext, PositionRecommendation


ADVISORY_ONLY_DISCLAIMER = (
    "This is advisory investment research only. Do not provide trading "
    "implementation steps, external account integration steps, or autonomous "
    "investment decisions. A human investor makes the final decision."
)


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
    advisory_only_disclaimer: str = ADVISORY_ONLY_DISCLAIMER

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
            "advisory_only_disclaimer",
            _required_text(
                self.advisory_only_disclaimer,
                "advisory_only_disclaimer",
            ),
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

    def build_prompts(
        self,
        contexts: tuple[CommitteePromptContext, ...],
    ) -> tuple[CommitteePersonaPrompt, ...]:
        """Build one prompt per supplied committee prompt context."""
        return tuple(self.build_prompt(context) for context in contexts)

    def build_prompt(self, context: CommitteePromptContext) -> CommitteePersonaPrompt:
        """Build a prompt for one permanent committee persona."""
        persona = context.persona
        prompt_text = "\n".join(
            [
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
                "Advisory Boundary",
                f"- {context.advisory_only_disclaimer}",
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
                f"- Quantity: {context.quantity:g}",
                f"- Market value: {context.market_value:g}",
                f"- Portfolio weight: {context.portfolio_weight:g}",
                f"- Cost basis: {_format_optional_number(context.cost_basis)}",
                (
                    "- Unrealized gain/loss: "
                    f"{_format_optional_number(context.unrealized_gain_loss)}"
                ),
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
