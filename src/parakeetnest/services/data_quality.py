"""Data quality models and validation services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import isfinite
from typing import Any

from parakeetnest.domain import (
    CalendarSnapshot,
    FinancialSnapshot,
    HoldingSnapshot,
    MacroSnapshot,
    MarketSnapshot,
    NewsSnapshot,
    PortfolioSnapshot,
)
from parakeetnest.exceptions import DataValidationError


class FreshnessStatus(StrEnum):
    """Freshness state for a normalized snapshot."""

    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class ValidationStatus(StrEnum):
    """Validation state for a normalized snapshot."""

    VALID = "valid"
    INVALID = "invalid"


@dataclass(frozen=True)
class DataQuality:
    """Describe snapshot source, freshness, completeness, and confidence."""

    source: str
    fetched_at: datetime | None
    freshness_status: FreshnessStatus
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    validation_status: ValidationStatus = ValidationStatus.INVALID
    confidence_score: float = 0.0

    @property
    def is_valid(self) -> bool:
        """Return whether the snapshot passed validation."""
        return self.validation_status is ValidationStatus.VALID


Snapshot = (
    PortfolioSnapshot
    | HoldingSnapshot
    | MarketSnapshot
    | FinancialSnapshot
    | NewsSnapshot
    | MacroSnapshot
    | CalendarSnapshot
)


REQUIRED_FIELDS: Mapping[type[Any], tuple[str, ...]] = {
    PortfolioSnapshot: ("source", "fetched_at", "holdings"),
    HoldingSnapshot: ("symbol", "quantity"),
    MarketSnapshot: ("source", "fetched_at", "symbol", "price"),
    FinancialSnapshot: ("source", "fetched_at", "symbol"),
    NewsSnapshot: ("source", "fetched_at", "title"),
    MacroSnapshot: ("source", "fetched_at", "indicator", "value"),
    CalendarSnapshot: ("source", "fetched_at", "event_type", "title"),
}

NUMERIC_MINIMUMS: Mapping[type[Any], Mapping[str, float | None]] = {
    PortfolioSnapshot: {"cash_balance": 0.0},
    HoldingSnapshot: {"quantity": 0.0, "cost_basis": 0.0, "market_value": 0.0},
    MarketSnapshot: {
        "price": 0.0,
        "daily_change": None,
        "volume": 0.0,
        "market_cap": 0.0,
        "pe_ratio": None,
        "eps": None,
    },
    FinancialSnapshot: {
        "revenue": None,
        "eps": None,
        "gross_margin": None,
        "operating_margin": None,
        "free_cash_flow": None,
    },
    MacroSnapshot: {"value": None},
}


def is_empty(value: object) -> bool:
    """Return whether a value should count as empty for validation."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, tuple | list | set | dict):
        return len(value) == 0
    return False


def validate_required_fields(snapshot: Snapshot) -> tuple[str, ...]:
    """Return required fields that are missing or empty."""
    missing = []
    for field_name in REQUIRED_FIELDS.get(type(snapshot), ()):
        if is_empty(getattr(snapshot, field_name, None)):
            missing.append(field_name)
    return tuple(missing)


def validate_invalid_numeric_values(snapshot: Snapshot) -> tuple[str, ...]:
    """Return numeric fields containing non-finite or out-of-range values."""
    invalid = []
    for field_name, minimum in NUMERIC_MINIMUMS.get(type(snapshot), {}).items():
        value = getattr(snapshot, field_name, None)
        if value is None:
            continue
        if not isinstance(value, int | float) or not isfinite(value):
            invalid.append(field_name)
            continue
        if minimum is not None and value < minimum:
            invalid.append(field_name)

    if isinstance(snapshot, PortfolioSnapshot):
        for index, holding in enumerate(snapshot.holdings):
            for field_name in validate_invalid_numeric_values(holding):
                invalid.append(f"holdings[{index}].{field_name}")
            for field_name in validate_required_fields(holding):
                invalid.append(f"holdings[{index}].{field_name}")

    return tuple(invalid)


def validate_snapshot_type(snapshot: object) -> None:
    """Raise when a value is not a supported normalized snapshot."""
    if type(snapshot) not in REQUIRED_FIELDS or not is_dataclass(snapshot):
        raise DataValidationError(f"Unsupported snapshot type: {type(snapshot)!r}")


def snapshot_source(snapshot: Snapshot) -> str:
    """Return a snapshot source when present."""
    return str(getattr(snapshot, "source", "unknown") or "unknown")


def snapshot_fetched_at(snapshot: Snapshot) -> datetime | None:
    """Return a snapshot fetch time when present."""
    value = getattr(snapshot, "fetched_at", None)
    return value if isinstance(value, datetime) else None


def freshness_status(
    fetched_at: datetime | None,
    *,
    now: datetime,
    max_age: timedelta,
) -> FreshnessStatus:
    """Return whether a fetch time is fresh, stale, or unknown."""
    if fetched_at is None:
        return FreshnessStatus.UNKNOWN
    normalized_fetched_at = fetched_at
    normalized_now = now
    if fetched_at.tzinfo is None and now.tzinfo is not None:
        normalized_now = now.replace(tzinfo=None)
    elif fetched_at.tzinfo is not None and now.tzinfo is None:
        normalized_fetched_at = fetched_at.astimezone(UTC).replace(tzinfo=None)
    if normalized_fetched_at > normalized_now:
        return FreshnessStatus.FRESH
    if normalized_now - normalized_fetched_at <= max_age:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


def dataclass_field_names(snapshot: object) -> tuple[str, ...]:
    """Return dataclass field names for diagnostics."""
    if not is_dataclass(snapshot):
        return ()
    return tuple(item.name for item in fields(snapshot))


class DataQualityService:
    """Validate normalized snapshots before they are saved or analyzed."""

    def __init__(self, max_age: timedelta = timedelta(days=1)) -> None:
        """Initialize the service with a freshness threshold."""
        self.max_age = max_age

    def validate(self, snapshot: Snapshot, now: datetime | None = None) -> DataQuality:
        """Validate a normalized snapshot and return its data quality report."""
        validate_snapshot_type(snapshot)
        checked_at = now or datetime.now(UTC)
        fetched_at = snapshot_fetched_at(snapshot)
        missing_fields = validate_required_fields(snapshot)
        numeric_errors = validate_invalid_numeric_values(snapshot)
        freshness = freshness_status(fetched_at, now=checked_at, max_age=self.max_age)
        invalid_fields = tuple(dict.fromkeys((*missing_fields, *numeric_errors)))
        validation_status = (
            ValidationStatus.VALID
            if not invalid_fields and freshness is FreshnessStatus.FRESH
            else ValidationStatus.INVALID
        )
        confidence_score = self._confidence_score(
            invalid_field_count=len(invalid_fields),
            total_field_count=max(len(dataclass_field_names(snapshot)), 1),
            freshness=freshness,
        )
        return DataQuality(
            source=snapshot_source(snapshot),
            fetched_at=fetched_at,
            freshness_status=freshness,
            missing_fields=invalid_fields,
            validation_status=validation_status,
            confidence_score=confidence_score,
        )

    def validate_before_saving(
        self,
        snapshot: Snapshot,
        now: datetime | None = None,
    ) -> DataQuality:
        """Validate a snapshot and raise if it should not be saved."""
        data_quality = self.validate(snapshot, now=now)
        if not data_quality.is_valid:
            raise DataValidationError(
                "Snapshot failed data quality validation: "
                f"{', '.join(data_quality.missing_fields) or data_quality.freshness_status}"
            )
        return data_quality

    def _confidence_score(
        self,
        *,
        invalid_field_count: int,
        total_field_count: int,
        freshness: FreshnessStatus,
    ) -> float:
        """Return a simple confidence score from 0.0 to 1.0."""
        completeness = max(0.0, 1.0 - (invalid_field_count / total_field_count))
        freshness_multiplier = {
            FreshnessStatus.FRESH: 1.0,
            FreshnessStatus.UNKNOWN: 0.6,
            FreshnessStatus.STALE: 0.2,
        }[freshness]
        return round(completeness * freshness_multiplier, 2)


class DataQualityValidator(DataQualityService):
    """Backward-compatible name for the data quality service."""
