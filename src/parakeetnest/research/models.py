"""Provider-neutral factual research context and committee report models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from parakeetnest.context.models import PortfolioSnapshot
from parakeetnest.models import (
    NewOpportunity,
    PortfolioDecisionSummary,
    PositionDecision,
)
from parakeetnest.portfolio.privacy import (
    PortfolioPositionContext,
    PortfolioSummary,
)


class ReportMode(str, Enum):
    """Advisory daily report mode."""

    MORNING = "morning"
    EVENING = "evening"

    @classmethod
    def from_value(cls, value: "ReportMode | str") -> "ReportMode":
        """Normalize a report mode value."""
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError("report mode must be morning or evening") from exc

    @property
    def title(self) -> str:
        """Return the reader-facing report title."""
        if self is ReportMode.EVENING:
            return "Evening Investment Review"
        return "Morning Investment Brief"


@dataclass(frozen=True)
class ResearchFinding:
    """One source-backed finding included in a research report."""

    summary: str
    source: str
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )


@dataclass(frozen=True)
class ResearchRisk:
    """One factual risk signal found in connected research context."""

    summary: str
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )


@dataclass(frozen=True)
class ResearchCatalyst:
    """One catalyst that could change the investment case."""

    summary: str
    horizon: str | None = None
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "horizon", _optional_text(self.horizon))
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )


@dataclass(frozen=True)
class ResearchFactInterpretation:
    """Ticker-specific interpretation of source-labeled public and portfolio facts."""

    valuation_label: str = "unavailable"
    valuation_summary: str = "Valuation facts are unavailable."
    risk_summary: str = "Risk interpretation is limited."
    catalyst_summary: str = "Catalyst evidence is limited."
    profile_summary: str = "Company profile facts are unavailable."
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        valuation_label = _required_text(
            self.valuation_label,
            "valuation_label",
        ).lower()
        allowed_labels = {
            "unavailable",
            "cheap",
            "fair",
            "expensive",
            "extreme",
            "revenue_multiple_risk",
        }
        if valuation_label not in allowed_labels:
            raise ValueError(
                "valuation label must be unavailable, cheap, fair, expensive, "
                "extreme, or revenue_multiple_risk"
            )
        object.__setattr__(self, "valuation_label", valuation_label)
        object.__setattr__(
            self,
            "valuation_summary",
            _required_text(self.valuation_summary, "valuation_summary"),
        )
        object.__setattr__(
            self,
            "risk_summary",
            _required_text(self.risk_summary, "risk_summary"),
        )
        object.__setattr__(
            self,
            "catalyst_summary",
            _required_text(self.catalyst_summary, "catalyst_summary"),
        )
        object.__setattr__(
            self,
            "profile_summary",
            _required_text(self.profile_summary, "profile_summary"),
        )
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )


@dataclass(frozen=True)
class ResearchCommitteeOpinion:
    """Daily-report opinion generated from a permanent committee persona."""

    persona_id: str
    display_name: str
    role_title: str
    stance: str
    reasoning_summary: str
    evidence_considered: tuple[str, ...]
    key_concern: str
    suggested_action: str
    responsibility: str
    viewpoint: str
    risk_posture: str
    evidence_requirements: tuple[str, ...]
    writing_style: str
    decision_biases_to_avoid: tuple[str, ...] = field(default_factory=tuple)

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
        stance = _required_text(self.stance, "stance").lower()
        if stance not in {"bullish", "neutral", "cautious"}:
            raise ValueError(
                "committee opinion stance must be bullish, neutral, or cautious"
            )
        object.__setattr__(self, "stance", stance)
        object.__setattr__(
            self,
            "reasoning_summary",
            _required_text(self.reasoning_summary, "reasoning_summary"),
        )
        object.__setattr__(
            self,
            "evidence_considered",
            _normalize_text_tuple(self.evidence_considered),
        )
        object.__setattr__(
            self,
            "key_concern",
            _required_text(self.key_concern, "key_concern"),
        )
        object.__setattr__(
            self,
            "suggested_action",
            _required_text(self.suggested_action, "suggested_action"),
        )
        object.__setattr__(
            self,
            "responsibility",
            _required_text(self.responsibility, "responsibility"),
        )
        object.__setattr__(
            self,
            "viewpoint",
            _required_text(self.viewpoint, "viewpoint"),
        )
        object.__setattr__(
            self,
            "risk_posture",
            _required_text(self.risk_posture, "risk_posture"),
        )
        object.__setattr__(
            self,
            "evidence_requirements",
            _normalize_text_tuple(self.evidence_requirements),
        )
        object.__setattr__(
            self,
            "writing_style",
            _required_text(self.writing_style, "writing_style"),
        )
        object.__setattr__(
            self,
            "decision_biases_to_avoid",
            _normalize_text_tuple(self.decision_biases_to_avoid),
        )
        if not self.evidence_requirements:
            raise ValueError("committee opinion evidence requirements are required")
        if not self.evidence_considered:
            raise ValueError("committee opinion evidence considered is required")


@dataclass(frozen=True)
class ResearchCommitteePortfolioView:
    """Portfolio-specific observation produced by committee discussion."""

    agent_name: str
    role: str
    portfolio_view: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "agent_name",
            _required_text(self.agent_name, "agent_name"),
        )
        object.__setattr__(self, "role", _required_text(self.role, "role"))
        object.__setattr__(
            self,
            "portfolio_view",
            _required_text(self.portfolio_view, "portfolio_view"),
        )


@dataclass(frozen=True)
class ResearchTickerReport:
    """Factual research context for one ticker before committee judgment."""

    ticker: str
    summary: str
    bull_case: tuple[str, ...]
    bear_case: tuple[str, ...]
    risks: tuple[ResearchRisk, ...]
    catalysts: tuple[ResearchCatalyst, ...]
    findings: tuple[ResearchFinding, ...] = field(default_factory=tuple)
    source_summaries: tuple[str, ...] = field(default_factory=tuple)
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)
    portfolio_summary: PortfolioSummary | None = None
    position_context: PortfolioPositionContext | None = None
    public_market_facts: tuple[str, ...] = field(default_factory=tuple)
    profile_facts: tuple[str, ...] = field(default_factory=tuple)
    valuation_facts: tuple[str, ...] = field(default_factory=tuple)
    financial_facts: tuple[str, ...] = field(default_factory=tuple)
    news_facts: tuple[str, ...] = field(default_factory=tuple)
    company_facts: tuple[str, ...] = field(default_factory=tuple)
    macro_facts: tuple[str, ...] = field(default_factory=tuple)
    fact_interpretation: ResearchFactInterpretation = field(
        default_factory=ResearchFactInterpretation
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _normalize_ticker(self.ticker))
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "bull_case", _normalize_text_tuple(self.bull_case))
        object.__setattr__(self, "bear_case", _normalize_text_tuple(self.bear_case))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(self, "catalysts", tuple(self.catalysts))
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(
            self,
            "source_summaries",
            _normalize_text_tuple(self.source_summaries),
        )
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )
        object.__setattr__(
            self,
            "public_market_facts",
            _normalize_text_tuple(self.public_market_facts),
        )
        object.__setattr__(
            self,
            "profile_facts",
            _normalize_text_tuple(self.profile_facts),
        )
        object.__setattr__(
            self,
            "valuation_facts",
            _normalize_text_tuple(self.valuation_facts),
        )
        object.__setattr__(
            self,
            "financial_facts",
            _normalize_text_tuple(self.financial_facts),
        )
        object.__setattr__(
            self,
            "news_facts",
            _normalize_text_tuple(self.news_facts),
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
            "fact_interpretation",
            self.fact_interpretation,
        )

    @property
    def evidence(self) -> tuple[str, ...]:
        """Return source-backed evidence summaries for committee consideration."""
        return _normalize_text_tuple(tuple(finding.summary for finding in self.findings))


@dataclass(frozen=True)
class ResearchCommitteeConsensus:
    """Final advisory investment judgment produced by the committee."""

    final_action: str
    confidence: str
    horizon: str
    rationale: str
    final_risk_posture: str
    todays_suggested_actions: tuple[str, ...]

    def __post_init__(self) -> None:
        action = _required_text(self.final_action, "final_action").lower()
        if action not in {"buy", "hold", "watch", "reduce", "sell"}:
            raise ValueError(
                "committee consensus final action must be buy, hold, watch, reduce, or sell"
            )
        confidence = _required_text(self.confidence, "confidence").lower()
        if confidence not in {"high", "medium", "low"}:
            raise ValueError("committee consensus confidence must be high, medium, or low")
        object.__setattr__(self, "final_action", action)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "horizon", _required_text(self.horizon, "horizon"))
        object.__setattr__(self, "rationale", _required_text(self.rationale, "rationale"))
        object.__setattr__(
            self,
            "final_risk_posture",
            _required_text(self.final_risk_posture, "final_risk_posture"),
        )
        object.__setattr__(
            self,
            "todays_suggested_actions",
            _normalize_text_tuple(self.todays_suggested_actions),
        )
        if not self.todays_suggested_actions:
            raise ValueError("committee consensus today's suggested actions are required")


@dataclass(frozen=True)
class ResearchPositionDecision:
    """Per-ticker committee review for daily research report cards."""

    ticker: str
    dongdong_opinion: str
    xixi_opinion: str
    youyou_opinion: str
    consensus: ResearchCommitteeConsensus
    recommendation: str
    confidence: str
    rationale: str
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _normalize_ticker(self.ticker))
        object.__setattr__(
            self,
            "dongdong_opinion",
            _required_text(self.dongdong_opinion, "dongdong_opinion"),
        )
        object.__setattr__(
            self,
            "xixi_opinion",
            _required_text(self.xixi_opinion, "xixi_opinion"),
        )
        object.__setattr__(
            self,
            "youyou_opinion",
            _required_text(self.youyou_opinion, "youyou_opinion"),
        )
        object.__setattr__(self, "consensus", self.consensus)
        recommendation = _required_text(self.recommendation, "recommendation").lower()
        if recommendation not in {"buy", "hold", "watch", "reduce", "sell"}:
            raise ValueError(
                "position decision recommendation must be buy, hold, watch, reduce, or sell"
            )
        confidence = _required_text(self.confidence, "confidence").lower()
        if confidence not in {"high", "medium", "low"}:
            raise ValueError("position decision confidence must be high, medium, or low")
        object.__setattr__(self, "recommendation", recommendation)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(
            self,
            "rationale",
            _required_text(self.rationale, "rationale"),
        )
        object.__setattr__(self, "evidence", _normalize_text_tuple(self.evidence))
        if not self.evidence:
            raise ValueError("position decision evidence is required")


@dataclass(frozen=True)
class InvestmentResearchReport:
    """Top-level daily investment research report payload."""

    ticker_reports: tuple[ResearchTickerReport, ...]
    mode: ReportMode | str = ReportMode.MORNING
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    title: str | None = None
    market_summary: str = "Market context is limited to connected research inputs."
    portfolio_review: str = "Portfolio review depends on connected portfolio context."
    watchlist_review: str = "Watchlist review depends on connected watchlist context."
    portfolio_context: PortfolioSnapshot | None = None
    committee_opinions: tuple[ResearchCommitteeOpinion, ...] = field(
        default_factory=tuple,
    )
    committee_portfolio_views: tuple[ResearchCommitteePortfolioView, ...] = field(
        default_factory=tuple,
    )
    committee_consensus: ResearchCommitteeConsensus = field(
        default_factory=lambda: ResearchCommitteeConsensus(
            final_action="watch",
            confidence="low",
            horizon="next research update",
            rationale="Committee consensus is based on limited connected evidence.",
            final_risk_posture="Advisory only; human investor makes the final decision.",
            todays_suggested_actions=("Review evidence before making any decision.",),
        )
    )
    position_committee_reviews: tuple[ResearchPositionDecision, ...] = field(
        default_factory=tuple
    )
    position_decisions: tuple[PositionDecision, ...] = field(default_factory=tuple)
    portfolio_decision_summary: PortfolioDecisionSummary | None = None
    new_opportunities: tuple[NewOpportunity, ...] = field(default_factory=tuple)
    source_summaries: tuple[str, ...] = field(default_factory=tuple)
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker_reports", tuple(self.ticker_reports))
        mode = ReportMode.from_value(self.mode)
        object.__setattr__(self, "mode", mode)
        if self.generated_at.tzinfo is None:
            object.__setattr__(
                self,
                "generated_at",
                self.generated_at.replace(tzinfo=UTC),
            )
        object.__setattr__(
            self,
            "title",
            _required_text(self.title or mode.title, "title"),
        )
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
        object.__setattr__(self, "committee_opinions", tuple(self.committee_opinions))
        object.__setattr__(
            self,
            "committee_portfolio_views",
            tuple(self.committee_portfolio_views),
        )
        object.__setattr__(
            self,
            "committee_consensus",
            self.committee_consensus,
        )
        object.__setattr__(
            self,
            "position_committee_reviews",
            tuple(self.position_committee_reviews),
        )
        object.__setattr__(
            self,
            "position_decisions",
            tuple(self.position_decisions),
        )
        object.__setattr__(
            self,
            "portfolio_decision_summary",
            self.portfolio_decision_summary,
        )
        object.__setattr__(
            self,
            "new_opportunities",
            tuple(self.new_opportunities),
        )
        object.__setattr__(
            self,
            "source_summaries",
            _normalize_text_tuple(self.source_summaries),
        )
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_text_tuple(self.evidence_notes),
        )

    def tickers(self) -> tuple[str, ...]:
        """Return ticker symbols in report order."""
        return tuple(ticker_report.ticker for ticker_report in self.ticker_reports)


def _normalize_ticker(value: str) -> str:
    ticker = str(value).strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    return ticker


def _required_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_text_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


__all__ = [
    "InvestmentResearchReport",
    "ReportMode",
    "ResearchCatalyst",
    "ResearchCommitteeConsensus",
    "ResearchCommitteeOpinion",
    "ResearchCommitteePortfolioView",
    "ResearchFinding",
    "ResearchPositionDecision",
    "ResearchRisk",
    "ResearchTickerReport",
]
