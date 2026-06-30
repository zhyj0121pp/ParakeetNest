"""Provider-agnostic Valuation Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ValuationMetric(str, Enum):
    """Common provider-independent valuation and quality metrics."""

    MARKET_CAP = "market_cap"
    ENTERPRISE_VALUE = "enterprise_value"
    PE_RATIO = "pe_ratio"
    FORWARD_PE_RATIO = "forward_pe_ratio"
    PS_RATIO = "ps_ratio"
    PB_RATIO = "pb_ratio"
    EV_TO_SALES = "ev_to_sales"
    EV_TO_EBITDA = "ev_to_ebitda"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    NET_MARGIN = "net_margin"
    REVENUE_GROWTH = "revenue_growth"
    EPS_GROWTH = "eps_growth"
    FREE_CASH_FLOW_YIELD = "free_cash_flow_yield"


class ValuationMethod(str, Enum):
    """Supported provider-neutral valuation approaches."""

    COMPARABLE_COMPANIES = "comparable_companies"
    DISCOUNTED_CASH_FLOW = "discounted_cash_flow"
    HISTORICAL_MULTIPLES = "historical_multiples"
    SUM_OF_THE_PARTS = "sum_of_the_parts"
    ASSET_BASED = "asset_based"
    OWNER_EARNINGS = "owner_earnings"


class ValuationConfidence(str, Enum):
    """Confidence level for valuation inputs and snapshots."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ValuationSnapshot:
    """Point-in-time provider-neutral valuation metrics for one symbol."""

    symbol: str
    as_of_date: date
    metrics: dict[ValuationMetric, float | None] = field(default_factory=dict)
    fiscal_period: str | None = None
    data_sources: list[str] = field(default_factory=list)
    calculation_notes: list[str] = field(default_factory=list)
    confidence: ValuationConfidence = ValuationConfidence.UNKNOWN

    def __post_init__(self) -> None:
        """Normalize stable identity and enum fields."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "metrics", _normalize_metrics(self.metrics))
        object.__setattr__(self, "data_sources", _clean_strings(self.data_sources))
        object.__setattr__(
            self,
            "calculation_notes",
            _clean_strings(self.calculation_notes),
        )
        if not isinstance(self.confidence, ValuationConfidence):
            object.__setattr__(
                self,
                "confidence",
                ValuationConfidence(self.confidence),
            )


@dataclass(frozen=True)
class ValuationInput:
    """Provider-neutral inputs prepared for a valuation method."""

    symbol: str
    method: ValuationMethod
    as_of_date: date
    metrics: dict[ValuationMetric, float | None] = field(default_factory=dict)
    fiscal_period: str | None = None
    assumptions: dict[str, float | str | None] = field(default_factory=dict)
    data_sources: list[str] = field(default_factory=list)
    calculation_notes: list[str] = field(default_factory=list)
    confidence: ValuationConfidence = ValuationConfidence.UNKNOWN

    def __post_init__(self) -> None:
        """Normalize request-like fields used by valuation services."""
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if not isinstance(self.method, ValuationMethod):
            object.__setattr__(self, "method", ValuationMethod(self.method))
        object.__setattr__(self, "metrics", _normalize_metrics(self.metrics))
        object.__setattr__(
            self,
            "assumptions",
            {
                key.strip(): value
                for key, value in self.assumptions.items()
                if key.strip()
            },
        )
        object.__setattr__(self, "data_sources", _clean_strings(self.data_sources))
        object.__setattr__(
            self,
            "calculation_notes",
            _clean_strings(self.calculation_notes),
        )
        if not isinstance(self.confidence, ValuationConfidence):
            object.__setattr__(
                self,
                "confidence",
                ValuationConfidence(self.confidence),
            )


def _normalize_metrics(
    metrics: dict[ValuationMetric | str, float | None],
) -> dict[ValuationMetric, float | None]:
    """Coerce metric keys to the provider-neutral enum."""
    return {ValuationMetric(metric): value for metric, value in metrics.items()}


def _clean_strings(values: list[str]) -> list[str]:
    """Remove blank strings while preserving source order."""
    return [value.strip() for value in values if value.strip()]


__all__ = [
    "ValuationConfidence",
    "ValuationInput",
    "ValuationMethod",
    "ValuationMetric",
    "ValuationSnapshot",
]
