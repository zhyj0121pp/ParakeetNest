"""Application service for provider-neutral position committee reviews."""

from __future__ import annotations

from dataclasses import dataclass, field

from parakeetnest.committee.prompting import (
    PersonaDrivenPositionReviewPromptBuilder,
    PositionReviewPromptBuilder,
)
from parakeetnest.llm import COMMITTEE_POSITION_REVIEW_SCHEMA, LLMProvider, LLMRequest
from parakeetnest.llm.parser import OutputParser
from parakeetnest.models import CommitteePositionReview, PositionContext


@dataclass
class PositionCommitteeReviewRunner:
    """Run Dongdong, Xixi, and Youyou reviews for one position context."""

    llm_provider: LLMProvider
    model: str = "mock-position-committee"
    temperature: float = 0.0
    prompt_builder: PositionReviewPromptBuilder = field(
        default_factory=PersonaDrivenPositionReviewPromptBuilder
    )
    parser: OutputParser = field(default_factory=OutputParser)

    def run(
        self,
        context: PositionContext,
    ) -> tuple[CommitteePositionReview, ...]:
        """Return committee reviews in Dongdong, Xixi, Youyou order."""
        reviews: list[CommitteePositionReview] = []
        for prompt in self.prompt_builder.build_prompts(context):
            response = self.llm_provider.complete(
                LLMRequest(
                    prompt=prompt.prompt_text,
                    model=self.model,
                    temperature=self.temperature,
                    response_schema=COMMITTEE_POSITION_REVIEW_SCHEMA,
                    metadata={
                        "symbol": context.symbol,
                        "persona_id": prompt.persona_id,
                        "agent_name": prompt.display_name,
                        "role": prompt.role_title,
                    },
                )
            )
            reviews.append(self.parser.parse_committee_position_review(response))
        return tuple(reviews)


__all__ = ["PositionCommitteeReviewRunner"]
