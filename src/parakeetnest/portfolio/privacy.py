"""Privacy-safe portfolio context for committee review."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioSummary:
    """Bucketed portfolio summary safe to send outside the local boundary."""

    number_of_positions: int
    cash_allocation_bucket: str
    concentration_level: str
    largest_position_bucket: str
    top5_concentration_bucket: str
    dominant_sector: str | None
    style_exposure: str
    privacy_level: str = "bucketed"


@dataclass(frozen=True)
class PortfolioPositionContext:
    """Bucketed per-position context safe for committee prompts."""

    ticker: str
    is_holding: bool
    position_size_bucket: str
    portfolio_rank_bucket: str
    unrealized_return_bucket: str
    holding_role: str
    add_allowed: bool
    trim_candidate: bool
    privacy_level: str = "bucketed"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", self.ticker.strip().upper())


class PortfolioPrivacyContextBuilder:
    """Convert local portfolio snapshots into privacy-safe bucketed context."""

    def build_summary(self, snapshot: Any | None) -> PortfolioSummary | None:
        """Return a privacy-safe portfolio summary."""
        positions = _positions(snapshot)
        if snapshot is None or not positions:
            return None

        weights = _position_weights(snapshot, positions)
        sorted_weights = sorted(weights.values(), reverse=True)
        largest_weight = sorted_weights[0] if sorted_weights else 0.0
        top5_weight = sum(sorted_weights[:5])
        cash_weight = _cash_weight(snapshot)
        return PortfolioSummary(
            number_of_positions=len(positions),
            cash_allocation_bucket=_cash_bucket(cash_weight),
            concentration_level=_concentration_level(largest_weight, top5_weight),
            largest_position_bucket=_weight_bucket(largest_weight),
            top5_concentration_bucket=_top5_bucket(top5_weight),
            dominant_sector=_dominant_sector(snapshot, positions),
            style_exposure=_style_exposure(positions),
        )

    def build_positions(
        self,
        snapshot: Any | None,
        tickers: tuple[str, ...],
    ) -> tuple[PortfolioPositionContext, ...]:
        """Return privacy-safe position context for requested tickers."""
        positions = _positions(snapshot)
        position_by_symbol = {_symbol(position): position for position in positions}
        weights = _position_weights(snapshot, positions)
        ranks = _rank_by_symbol(weights)
        summary = self.build_summary(snapshot)
        concentration_level = (
            summary.concentration_level if summary is not None else "unknown"
        )
        contexts: list[PortfolioPositionContext] = []
        for ticker in tickers:
            symbol = ticker.strip().upper()
            position = position_by_symbol.get(symbol)
            weight = weights.get(symbol, 0.0)
            return_pct = _unrealized_return(position)
            size_bucket = _weight_bucket(weight) if position is not None else "none"
            return_bucket = (
                _return_bucket(return_pct) if position is not None else "not_holding"
            )
            trim_candidate = (
                position is not None
                and (
                    size_bucket in {"large", "very_large"}
                    or concentration_level in {"high", "very_high"}
                )
            )
            contexts.append(
                PortfolioPositionContext(
                    ticker=symbol,
                    is_holding=position is not None,
                    position_size_bucket=size_bucket,
                    portfolio_rank_bucket=(
                        _rank_bucket(ranks.get(symbol))
                        if position is not None
                        else "not_holding"
                    ),
                    unrealized_return_bucket=return_bucket,
                    holding_role=_holding_role(position, weight),
                    add_allowed=position is None or (
                        size_bucket not in {"large", "very_large"}
                        and concentration_level not in {"high", "very_high"}
                    ),
                    trim_candidate=trim_candidate,
                )
            )
        return tuple(contexts)

    def build(
        self,
        snapshot: Any | None,
        tickers: tuple[str, ...],
    ) -> tuple[PortfolioSummary | None, tuple[PortfolioPositionContext, ...]]:
        """Return summary and requested position contexts."""
        return self.build_summary(snapshot), self.build_positions(snapshot, tickers)


def _positions(snapshot: Any | None) -> tuple[Any, ...]:
    if snapshot is None:
        return ()
    return tuple(
        getattr(snapshot, "positions", ())
        or getattr(snapshot, "holdings", ())
        or ()
    )


def _symbol(position: Any) -> str:
    return str(getattr(position, "symbol", getattr(position, "ticker", ""))).upper()


def _position_weights(snapshot: Any, positions: tuple[Any, ...]) -> dict[str, float]:
    explicit = {
        _symbol(position): float(getattr(position, "weight"))
        for position in positions
        if getattr(position, "weight", None) is not None
    }
    if explicit:
        return explicit

    total_value = (
        getattr(snapshot, "total_value", None)
        or getattr(snapshot, "total_equity", None)
        or getattr(snapshot, "total_market_value", None)
    )
    if total_value in (None, 0):
        return {_symbol(position): 0.0 for position in positions}
    return {
        _symbol(position): float(getattr(position, "market_value", 0.0) or 0.0)
        / float(total_value)
        for position in positions
    }


def _rank_by_symbol(weights: dict[str, float]) -> dict[str, int]:
    return {
        symbol: index + 1
        for index, (symbol, _) in enumerate(
            sorted(weights.items(), key=lambda item: item[1], reverse=True)
        )
    }


def _cash_weight(snapshot: Any) -> float:
    total_value = (
        getattr(snapshot, "total_value", None)
        or getattr(snapshot, "total_equity", None)
        or getattr(snapshot, "total_market_value", None)
    )
    cash = getattr(snapshot, "cash_balance", None) or getattr(snapshot, "total_cash", None)
    if total_value in (None, 0) or cash is None:
        return 0.0
    return float(cash) / float(total_value)


def _unrealized_return(position: Any | None) -> float | None:
    if position is None:
        return None
    explicit = getattr(position, "unrealized_gain_loss_percent", None)
    if explicit is not None:
        return float(explicit)
    unrealized_pl = getattr(position, "unrealized_pl", None)
    if unrealized_pl is None:
        unrealized_pl = getattr(position, "unrealized_gain_loss", None)
    cost_basis = getattr(position, "cost_basis", None)
    if cost_basis is None:
        quantity = getattr(position, "quantity", None)
        average_cost = getattr(position, "average_cost", None)
        if quantity is not None and average_cost is not None:
            cost_basis = float(quantity) * float(average_cost)
    if unrealized_pl is None or cost_basis in (None, 0):
        return None
    return float(unrealized_pl) / float(cost_basis)


def _cash_bucket(weight: float) -> str:
    if weight < 0.02:
        return "very_low"
    if weight < 0.10:
        return "low"
    if weight < 0.25:
        return "moderate"
    return "high"


def _weight_bucket(weight: float) -> str:
    if weight <= 0:
        return "none"
    if weight < 0.03:
        return "tiny"
    if weight < 0.08:
        return "small"
    if weight < 0.15:
        return "medium"
    if weight < 0.30:
        return "large"
    return "very_large"


def _top5_bucket(weight: float) -> str:
    if weight < 0.25:
        return "low"
    if weight < 0.50:
        return "moderate"
    if weight < 0.75:
        return "high"
    return "very_high"


def _concentration_level(largest_weight: float, top5_weight: float) -> str:
    if largest_weight >= 0.30 or top5_weight >= 0.75:
        return "very_high"
    if largest_weight >= 0.20 or top5_weight >= 0.60:
        return "high"
    if largest_weight >= 0.10 or top5_weight >= 0.40:
        return "moderate"
    return "low"


def _return_bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value <= -0.30:
        return "large_loss"
    if value <= -0.10:
        return "loss"
    if value < 0.10:
        return "flat"
    if value < 0.30:
        return "gain"
    return "large_gain"


def _rank_bucket(rank: int | None) -> str:
    if rank is None:
        return "unknown"
    if rank == 1:
        return "largest"
    if rank <= 3:
        return "top_3"
    if rank <= 5:
        return "top_5"
    return "outside_top_5"


def _holding_role(position: Any | None, weight: float) -> str:
    if position is None:
        return "not_holding"
    sector = getattr(position, "sector", None)
    if weight >= 0.15:
        return "core_holding"
    if sector:
        return "sector_exposure"
    return "satellite_holding"


def _dominant_sector(snapshot: Any, positions: tuple[Any, ...]) -> str | None:
    allocations = getattr(snapshot, "allocation_by_sector", ()) or ()
    if allocations:
        largest = max(allocations, key=lambda item: getattr(item, "percent", 0.0))
        return str(getattr(largest, "category", "")).strip() or None
    sectors = Counter(
        str(getattr(position, "sector", "")).strip()
        for position in positions
        if str(getattr(position, "sector", "")).strip()
    )
    if not sectors:
        return None
    return sectors.most_common(1)[0][0]


def _style_exposure(positions: tuple[Any, ...]) -> str:
    sectors = {
        str(getattr(position, "sector", "")).strip().lower()
        for position in positions
        if str(getattr(position, "sector", "")).strip()
    }
    if {"technology", "communication services"} & sectors:
        return "growth_tilt"
    if {"utilities", "consumer staples", "healthcare"} & sectors:
        return "defensive_tilt"
    return "mixed"


__all__ = [
    "PortfolioPositionContext",
    "PortfolioPrivacyContextBuilder",
    "PortfolioSummary",
]
