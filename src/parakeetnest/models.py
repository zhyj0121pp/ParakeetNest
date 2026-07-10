"""Shared domain models for ParakeetNest."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class RecommendationAction(StrEnum):
    """Supported investment recommendation actions."""

    BUY = "buy"
    HOLD = "hold"
    REDUCE = "reduce"
    WATCH = "watch"


class ConfidenceLevel(StrEnum):
    """Human-readable confidence levels for committee conclusions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PositionRecommendation(StrEnum):
    """Supported position-level investment recommendations."""

    BUY_MORE = "buy_more"
    HOLD = "hold"
    TRIM = "trim"
    SELL = "sell"
    WATCH = "watch"
    NO_ACTION = "no_action"


class DecisionUrgency(StrEnum):
    """Urgency levels for position-level decisions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class InvestmentHorizon(StrEnum):
    """Supported investment horizons."""

    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    ONE_YEAR = "1_year"
    THREE_YEARS = "3_years"


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of supporting evidence with source attribution."""

    summary: str
    source: str
    observed_at: datetime | None = None


@dataclass(frozen=True)
class Recommendation:
    """A complete committee recommendation.

    Every recommendation includes action, confidence, horizon, evidence,
    risks, and catalysts as required by the project rules.
    """

    symbol: str
    action: RecommendationAction
    confidence: ConfidenceLevel
    horizon: InvestmentHorizon
    evidence: tuple[EvidenceItem, ...]
    risks: tuple[str, ...]
    catalysts: tuple[str, ...]
    data_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    created_at: datetime | None = None


@dataclass(frozen=True)
class CommitteeMemo:
    """A role-specific committee note produced during a meeting."""

    role: str
    symbol: str
    summary: str
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    catalysts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CommitteePositionReview:
    """One committee member's structured review of an existing position."""

    symbol: str
    agent_name: str
    thesis: str
    concerns: tuple[str, ...]
    recommendation: PositionRecommendation | str
    confidence: ConfidenceLevel | str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        """Normalize review identity, enums, and immutable evidence fields."""
        object.__setattr__(self, "symbol", _required_symbol(self.symbol))
        object.__setattr__(
            self,
            "agent_name",
            _required_text(self.agent_name, "agent_name"),
        )
        object.__setattr__(self, "thesis", _required_text(self.thesis, "thesis"))
        object.__setattr__(self, "concerns", _text_tuple(self.concerns, "concerns"))
        object.__setattr__(
            self,
            "recommendation",
            _position_recommendation(self.recommendation),
        )
        object.__setattr__(self, "confidence", _confidence_level(self.confidence))
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(self.evidence_refs, "evidence_refs", require_non_empty=True),
        )


@dataclass(frozen=True)
class PositionContext:
    """Provider-neutral evidence packet for reviewing one current position."""

    symbol: str
    company_name: str
    quantity: float
    market_value: float
    portfolio_weight: float
    cost_basis: float | None = None
    unrealized_gain_loss: float | None = None
    current_price: float | None = None
    recent_price_change: float | None = None
    relevant_news: tuple[str, ...] = field(default_factory=tuple)
    relevant_research: tuple[str, ...] = field(default_factory=tuple)
    risk_notes: tuple[str, ...] = field(default_factory=tuple)
    valuation_notes: tuple[str, ...] = field(default_factory=tuple)
    momentum_notes: tuple[str, ...] = field(default_factory=tuple)
    portfolio_notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize context fields while staying provider-neutral."""
        object.__setattr__(self, "symbol", _required_symbol(self.symbol))
        object.__setattr__(
            self,
            "company_name",
            _required_text(self.company_name, "company_name"),
        )
        object.__setattr__(self, "quantity", float(self.quantity))
        object.__setattr__(self, "market_value", float(self.market_value))
        object.__setattr__(self, "portfolio_weight", float(self.portfolio_weight))
        for field_name in (
            "relevant_news",
            "relevant_research",
            "risk_notes",
            "valuation_notes",
            "momentum_notes",
            "portfolio_notes",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )
        for field_name in (
            "cost_basis",
            "unrealized_gain_loss",
            "current_price",
            "recent_price_change",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, float(value))


@dataclass(frozen=True)
class PositionDecision:
    """Final Chairman decision for a current portfolio position."""

    symbol: str
    company_name: str
    recommendation: PositionRecommendation | str
    action_required: bool
    urgency: DecisionUrgency | str
    final_rationale: str
    dongdong_opinion: str
    xixi_opinion: str
    yoyo_opinion: str
    factual_evidence: tuple[str, ...]
    risks: tuple[str, ...]
    confidence: ConfidenceLevel | str
    human_review_required: bool

    def __post_init__(self) -> None:
        """Normalize decision fields without introducing provider concerns."""
        object.__setattr__(self, "symbol", _required_symbol(self.symbol))
        object.__setattr__(
            self,
            "company_name",
            _required_text(self.company_name, "company_name"),
        )
        object.__setattr__(
            self,
            "recommendation",
            _position_recommendation(self.recommendation),
        )
        object.__setattr__(
            self,
            "action_required",
            _required_bool(self.action_required, "action_required"),
        )
        object.__setattr__(self, "urgency", _decision_urgency(self.urgency))
        object.__setattr__(
            self,
            "final_rationale",
            _required_text(self.final_rationale, "final_rationale"),
        )
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
            "yoyo_opinion",
            _required_text(self.yoyo_opinion, "yoyo_opinion"),
        )
        object.__setattr__(
            self,
            "factual_evidence",
            _text_tuple(
                self.factual_evidence,
                "factual_evidence",
                require_non_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "risks",
            _text_tuple(self.risks, "risks", require_non_empty=True),
        )
        object.__setattr__(self, "confidence", _confidence_level(self.confidence))
        object.__setattr__(
            self,
            "human_review_required",
            _required_bool(self.human_review_required, "human_review_required"),
        )
        _validate_position_decision(self)


@dataclass(frozen=True)
class PortfolioDecisionSummary:
    """Portfolio-level summary of position decisions and non-actions."""

    overall_portfolio_view: str
    concentration_risks: tuple[str, ...]
    sector_exposure_notes: tuple[str, ...]
    cash_allocation_notes: tuple[str, ...]
    action_items: tuple[str, ...]
    no_action_positions: tuple[str, ...]

    def __post_init__(self) -> None:
        """Normalize summary collections for stable downstream rendering."""
        object.__setattr__(
            self,
            "overall_portfolio_view",
            _required_text(
                self.overall_portfolio_view,
                "overall_portfolio_view",
            ),
        )
        object.__setattr__(
            self,
            "concentration_risks",
            _text_tuple(self.concentration_risks, "concentration_risks"),
        )
        object.__setattr__(
            self,
            "sector_exposure_notes",
            _text_tuple(self.sector_exposure_notes, "sector_exposure_notes"),
        )
        object.__setattr__(
            self,
            "cash_allocation_notes",
            _text_tuple(self.cash_allocation_notes, "cash_allocation_notes"),
        )
        object.__setattr__(
            self,
            "action_items",
            _text_tuple(self.action_items, "action_items"),
        )
        object.__setattr__(
            self,
            "no_action_positions",
            tuple(_required_symbol(symbol) for symbol in self.no_action_positions),
        )


@dataclass(frozen=True)
class NewOpportunity:
    """Provider-neutral decision candidate for a new investment opportunity."""

    symbol: str
    company_name: str
    opportunity_type: str
    rationale: str
    risks: tuple[str, ...]
    suggested_action: PositionRecommendation | str
    confidence: ConfidenceLevel | str

    def __post_init__(self) -> None:
        """Normalize opportunity fields without execution semantics."""
        object.__setattr__(self, "symbol", _required_symbol(self.symbol))
        object.__setattr__(
            self,
            "company_name",
            _required_text(self.company_name, "company_name"),
        )
        object.__setattr__(
            self,
            "opportunity_type",
            _required_text(self.opportunity_type, "opportunity_type"),
        )
        object.__setattr__(
            self,
            "rationale",
            _required_text(self.rationale, "rationale"),
        )
        object.__setattr__(
            self,
            "risks",
            _text_tuple(self.risks, "risks", require_non_empty=True),
        )
        object.__setattr__(
            self,
            "suggested_action",
            _position_recommendation(self.suggested_action),
        )
        object.__setattr__(self, "confidence", _confidence_level(self.confidence))


def _required_symbol(value: str) -> str:
    """Return a normalized non-empty ticker symbol."""
    symbol = value.strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    return symbol


def _required_text(value: str, field_name: str) -> str:
    """Return stripped required text."""
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _required_bool(value: bool, field_name: str) -> bool:
    """Return a real bool value without truthiness coercion."""
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool")
    return value


def _text_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    require_non_empty: bool = False,
) -> tuple[str, ...]:
    """Return stripped text values as an immutable tuple."""
    normalized = tuple(value.strip() for value in values if value.strip())
    if require_non_empty and not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _position_recommendation(
    value: PositionRecommendation | str,
) -> PositionRecommendation:
    """Coerce position recommendation strings into the domain enum."""
    if isinstance(value, PositionRecommendation):
        return value
    return PositionRecommendation(value.strip().lower())


def _decision_urgency(value: DecisionUrgency | str) -> DecisionUrgency:
    """Coerce urgency strings into the domain enum."""
    if isinstance(value, DecisionUrgency):
        return value
    return DecisionUrgency(value.strip().lower())


def _confidence_level(value: ConfidenceLevel | str) -> ConfidenceLevel:
    """Coerce confidence strings into the shared confidence enum."""
    if isinstance(value, ConfidenceLevel):
        return value
    return ConfidenceLevel(value.strip().lower())


def _validate_position_decision(decision: PositionDecision) -> None:
    """Validate cross-field position decision invariants."""
    if decision.recommendation is PositionRecommendation.NO_ACTION:
        if decision.action_required:
            raise ValueError("NO_ACTION decisions cannot require action")
        if decision.urgency is not DecisionUrgency.NONE:
            raise ValueError("NO_ACTION decisions must have NONE urgency")

    review_required_recommendations = (
        PositionRecommendation.BUY_MORE,
        PositionRecommendation.TRIM,
        PositionRecommendation.SELL,
    )
    if (
        decision.recommendation in review_required_recommendations
        and not decision.human_review_required
    ):
        raise ValueError(
            "BUY_MORE, TRIM, and SELL decisions require human review"
        )
