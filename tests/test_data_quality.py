"""Tests for normalized domain snapshots and data quality validation."""

from datetime import UTC, datetime, timedelta

import pytest

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
from parakeetnest.services.data_quality import (
    DataQualityService,
    FreshnessStatus,
    ValidationStatus,
)


def test_valid_market_snapshot_passes_data_quality() -> None:
    """Fresh snapshots with required fields and valid numbers should pass."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = MarketSnapshot(
        source="manual",
        fetched_at=now,
        symbol="NVDA",
        price=100.0,
        volume=1_000_000.0,
    )

    data_quality = DataQualityService().validate(snapshot, now=now)

    assert data_quality.validation_status is ValidationStatus.VALID
    assert data_quality.freshness_status is FreshnessStatus.FRESH
    assert data_quality.missing_fields == ()
    assert data_quality.confidence_score == 1.0


def test_required_fields_are_reported_for_empty_values() -> None:
    """Blank required strings should be treated as missing fields."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = NewsSnapshot(source="manual", fetched_at=now, title=" ")

    data_quality = DataQualityService().validate(snapshot, now=now)

    assert data_quality.validation_status is ValidationStatus.INVALID
    assert data_quality.missing_fields == ("title",)


def test_stale_data_is_invalid_even_when_required_fields_exist() -> None:
    """Snapshots older than the configured freshness window should fail."""
    now = datetime(2026, 1, 2, tzinfo=UTC)
    snapshot = MacroSnapshot(
        source="manual",
        fetched_at=now - timedelta(days=3),
        indicator="fed_funds_rate",
        value=5.0,
    )

    data_quality = DataQualityService(max_age=timedelta(days=1)).validate(
        snapshot,
        now=now,
    )

    assert data_quality.validation_status is ValidationStatus.INVALID
    assert data_quality.freshness_status is FreshnessStatus.STALE
    assert data_quality.confidence_score == 0.2


def test_missing_fetch_time_has_unknown_freshness() -> None:
    """Missing fetch timestamps should be explicit in the freshness result."""
    snapshot = CalendarSnapshot(
        source="manual",
        fetched_at=None,
        event_type="earnings",
        title="NVDA earnings",
    )

    data_quality = DataQualityService().validate(snapshot)

    assert data_quality.validation_status is ValidationStatus.INVALID
    assert data_quality.freshness_status is FreshnessStatus.UNKNOWN
    assert "fetched_at" in data_quality.missing_fields


def test_invalid_numeric_values_are_reported() -> None:
    """Negative nonnegative fields and non-finite numbers should fail."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = MarketSnapshot(
        source="manual",
        fetched_at=now,
        symbol="NVDA",
        price=-1.0,
        volume=float("nan"),
        daily_change=-2.5,
    )

    data_quality = DataQualityService().validate(snapshot, now=now)

    assert data_quality.validation_status is ValidationStatus.INVALID
    assert "price" in data_quality.missing_fields
    assert "volume" in data_quality.missing_fields
    assert "daily_change" not in data_quality.missing_fields


def test_portfolio_validation_checks_nested_holdings() -> None:
    """Portfolio validation should include nested holding quality checks."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot = PortfolioSnapshot(
        source="manual",
        fetched_at=now,
        holdings=(HoldingSnapshot(symbol="", quantity=-1.0),),
        cash_balance=100.0,
    )

    data_quality = DataQualityService().validate(snapshot, now=now)

    assert data_quality.validation_status is ValidationStatus.INVALID
    assert "holdings[0].symbol" in data_quality.missing_fields
    assert "holdings[0].quantity" in data_quality.missing_fields


def test_validate_before_saving_rejects_invalid_snapshot() -> None:
    """Invalid snapshots should be blocked before persistence."""
    snapshot = FinancialSnapshot(
        source="manual",
        fetched_at=None,
        symbol="",
    )

    with pytest.raises(DataValidationError):
        DataQualityService().validate_before_saving(snapshot)


def test_all_snapshot_types_can_be_validated() -> None:
    """Every normalized snapshot type should be accepted by the service."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    snapshots = (
        PortfolioSnapshot(
            source="manual",
            fetched_at=now,
            holdings=(HoldingSnapshot(symbol="AAPL", quantity=1.0),),
        ),
        MarketSnapshot(source="manual", fetched_at=now, symbol="AAPL", price=1.0),
        FinancialSnapshot(source="manual", fetched_at=now, symbol="AAPL"),
        NewsSnapshot(source="manual", fetched_at=now, title="AAPL news"),
        MacroSnapshot(
            source="manual",
            fetched_at=now,
            indicator="cpi",
            value=1.0,
        ),
        CalendarSnapshot(
            source="manual",
            fetched_at=now,
            event_type="earnings",
            title="AAPL earnings",
        ),
    )

    service = DataQualityService()

    assert all(service.validate(snapshot, now=now).is_valid for snapshot in snapshots)
