"""Provider-neutral persona-driven committee prompt models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from parakeetnest.committee.personas import CommitteePersona


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


def _render_items(values: tuple[str, ...]) -> list[str]:
    normalized = _normalize_text_tuple(values)
    if not normalized:
        return ["  - None supplied."]
    return [f"  - {value}" for value in normalized]


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
    "PersonaDrivenCommitteePromptBuilder",
]
