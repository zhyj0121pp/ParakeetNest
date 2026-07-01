"""Provider-neutral investment research report domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class RecommendationType(StrEnum):
    """Provider-neutral recommendation actions for research reports."""

    BUY = "buy"
    HOLD = "hold"
    WATCH = "watch"
    REDUCE = "reduce"
    SELL = "sell"


class ConfidenceLevel(StrEnum):
    """Human-readable confidence levels for research conclusions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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
    """One risk that should travel with the recommendation."""

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
class ResearchRecommendation:
    """Complete recommendation payload required by project rules."""

    action: RecommendationType
    confidence: ConfidenceLevel
    horizon: str
    evidence: tuple[str, ...]
    risks: tuple[str, ...]
    catalysts: tuple[str, ...]
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, RecommendationType):
            object.__setattr__(self, "action", RecommendationType(self.action))
        if not isinstance(self.confidence, ConfidenceLevel):
            object.__setattr__(self, "confidence", ConfidenceLevel(self.confidence))
        object.__setattr__(self, "horizon", _required_text(self.horizon, "horizon"))
        object.__setattr__(self, "evidence", _normalize_text_tuple(self.evidence))
        object.__setattr__(self, "risks", _normalize_text_tuple(self.risks))
        object.__setattr__(self, "catalysts", _normalize_text_tuple(self.catalysts))
        object.__setattr__(self, "rationale", _optional_text(self.rationale))
        if not self.evidence:
            raise ValueError("recommendation evidence is required")
        if not self.risks:
            raise ValueError("recommendation risks are required")
        if not self.catalysts:
            raise ValueError("recommendation catalysts are required")


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
class ResearchTickerReport:
    """Email-ready research synthesis for one ticker."""

    ticker: str
    summary: str
    bull_case: tuple[str, ...]
    bear_case: tuple[str, ...]
    risks: tuple[ResearchRisk, ...]
    catalysts: tuple[ResearchCatalyst, ...]
    recommendation: ResearchRecommendation
    findings: tuple[ResearchFinding, ...] = field(default_factory=tuple)
    source_summaries: tuple[str, ...] = field(default_factory=tuple)
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

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

    @property
    def confidence(self) -> ConfidenceLevel:
        """Return the recommendation confidence for convenient rendering."""
        return self.recommendation.confidence


@dataclass(frozen=True)
class InvestmentResearchReport:
    """Top-level daily investment research report payload."""

    ticker_reports: tuple[ResearchTickerReport, ...]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    title: str = "Investment Research Report"
    market_summary: str = "Market context is limited to connected research inputs."
    portfolio_review: str = "Portfolio review depends on connected portfolio context."
    watchlist_review: str = "Watchlist review depends on connected watchlist context."
    committee_opinions: tuple[ResearchCommitteeOpinion, ...] = field(
        default_factory=tuple,
    )
    committee_consensus: str = (
        "Committee consensus is based on the current evidence set."
    )
    todays_suggested_actions: tuple[str, ...] = field(default_factory=tuple)
    source_summaries: tuple[str, ...] = field(default_factory=tuple)
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker_reports", tuple(self.ticker_reports))
        if self.generated_at.tzinfo is None:
            object.__setattr__(
                self,
                "generated_at",
                self.generated_at.replace(tzinfo=UTC),
            )
        object.__setattr__(self, "title", _required_text(self.title, "title"))
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
            "committee_consensus",
            _required_text(self.committee_consensus, "committee_consensus"),
        )
        object.__setattr__(
            self,
            "todays_suggested_actions",
            _normalize_text_tuple(self.todays_suggested_actions),
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
    "ConfidenceLevel",
    "InvestmentResearchReport",
    "RecommendationType",
    "ResearchCatalyst",
    "ResearchCommitteeOpinion",
    "ResearchFinding",
    "ResearchRecommendation",
    "ResearchRisk",
    "ResearchTickerReport",
]
