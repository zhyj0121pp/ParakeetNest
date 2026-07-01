"""Tests for Watchlist Intelligence domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, fields
from datetime import UTC, datetime

import pytest

from parakeetnest.watchlist import (
    WatchlistInsight,
    WatchlistItem,
    WatchlistPriority,
    WatchlistSignal,
    WatchlistStatus,
    WatchlistThesis,
)


CREATED_AT = datetime(2026, 7, 1, 13, 30, tzinfo=UTC)


def test_watchlist_priority_values_are_stable() -> None:
    """Priority values should describe attention level, not providers."""
    assert WatchlistPriority.HIGH.value == "high"
    assert WatchlistPriority.MEDIUM.value == "medium"
    assert WatchlistPriority.LOW.value == "low"


def test_watchlist_status_values_are_stable() -> None:
    """Status values should describe watchlist lifecycle state."""
    assert WatchlistStatus.ACTIVE.value == "active"
    assert WatchlistStatus.PAUSED.value == "paused"
    assert WatchlistStatus.ARCHIVED.value == "archived"


def test_watchlist_item_defaults_priority_status_and_timestamps() -> None:
    """The default watchlist item should be active and medium priority."""
    item = WatchlistItem(symbol=" nvda ", created_at=CREATED_AT)

    assert item.symbol == "NVDA"
    assert item.priority is WatchlistPriority.MEDIUM
    assert item.status is WatchlistStatus.ACTIVE
    assert item.notes == ()
    assert item.created_at == CREATED_AT
    assert item.updated_at == CREATED_AT

    with pytest.raises(FrozenInstanceError):
        item.symbol = "AMD"


def test_watchlist_item_construction_normalizes_optional_fields() -> None:
    """Items should normalize text and accept enum string values."""
    item = WatchlistItem(
        symbol=" msft ",
        company_name=" Microsoft Corporation ",
        sector=" Technology ",
        theme=" AI infrastructure ",
        reason=" Strong platform leverage ",
        priority="high",
        status="paused",
        notes=[" Azure demand ", ""],
        created_at=CREATED_AT,
    )

    assert item.symbol == "MSFT"
    assert item.company_name == "Microsoft Corporation"
    assert item.sector == "Technology"
    assert item.theme == "AI infrastructure"
    assert item.reason == "Strong platform leverage"
    assert item.priority is WatchlistPriority.HIGH
    assert item.status is WatchlistStatus.PAUSED
    assert item.notes == ("Azure demand",)


def test_watchlist_thesis_construction() -> None:
    """A thesis should capture drivers, risks, horizon, and confidence."""
    thesis = WatchlistThesis(
        symbol=" aapl ",
        thesis="Services mix can support durable margins.",
        key_drivers=[" installed base ", " services growth "],
        risks=[" China demand "],
        time_horizon=" 12-18 months ",
        confidence="0.72",
    )

    assert thesis.symbol == "AAPL"
    assert thesis.thesis == "Services mix can support durable margins."
    assert thesis.key_drivers == ("installed base", "services growth")
    assert thesis.risks == ("China demand",)
    assert thesis.time_horizon == "12-18 months"
    assert thesis.confidence == 0.72


def test_watchlist_signal_construction() -> None:
    """A signal should capture a provider-neutral watchlist event."""
    signal = WatchlistSignal(
        symbol=" tsla ",
        signal_type=" Delivery_Momentum ",
        summary="Consensus revisions are improving.",
        strength="0.8",
        source=" internal research ",
    )

    assert signal.symbol == "TSLA"
    assert signal.signal_type == "delivery_momentum"
    assert signal.summary == "Consensus revisions are improving."
    assert signal.strength == 0.8
    assert signal.source == "internal research"


def test_watchlist_insight_construction() -> None:
    """An insight should hold balanced bull, bear, and question fields."""
    insight = WatchlistInsight(
        symbol=" amd ",
        summary="AI accelerator share gains remain plausible but contested.",
        bullish_factors=[" MI-series traction "],
        bearish_factors=[" margin pressure "],
        open_questions=[" Can supply scale? "],
        recommended_action=" keep active ",
    )

    assert insight.symbol == "AMD"
    assert insight.bullish_factors == ("MI-series traction",)
    assert insight.bearish_factors == ("margin pressure",)
    assert insight.open_questions == ("Can supply scale?",)
    assert insight.recommended_action == "keep active"


def test_default_list_fields_are_not_shared_across_instances() -> None:
    """Default collections should be immutable and instance-safe."""
    first = WatchlistInsight(symbol="NVDA", summary="First")
    second = WatchlistInsight(symbol="MSFT", summary="Second")
    field_by_name = {field.name: field for field in fields(WatchlistInsight)}

    assert first.bullish_factors == ()
    assert second.bullish_factors == ()
    assert field_by_name["bullish_factors"].default_factory is tuple
    assert not hasattr(first.bullish_factors, "append")


def test_source_lists_are_not_shared_after_construction() -> None:
    """Model construction should detach from mutable source lists."""
    notes = ["first"]
    drivers = ["driver"]

    item = WatchlistItem(symbol="NVDA", notes=notes, created_at=CREATED_AT)
    thesis = WatchlistThesis(
        symbol="NVDA",
        thesis="AI demand can compound.",
        key_drivers=drivers,
    )
    notes.append("late")
    drivers.append("late")

    assert item.notes == ("first",)
    assert thesis.key_drivers == ("driver",)


def test_watchlist_models_support_basic_dataclass_serialization() -> None:
    """Dataclass serialization should expose stable model fields."""
    item = WatchlistItem(
        symbol=" nvda ",
        priority=WatchlistPriority.HIGH,
        created_at=CREATED_AT,
    )

    payload = asdict(item)

    assert payload["symbol"] == "NVDA"
    assert payload["priority"] is WatchlistPriority.HIGH
    assert payload["status"] is WatchlistStatus.ACTIVE
    assert payload["notes"] == ()
    assert payload["created_at"] == CREATED_AT


def test_public_models_are_exported_from_watchlist_package() -> None:
    """The package should expose the public watchlist model surface."""
    import parakeetnest.watchlist as watchlist

    assert watchlist.WatchlistItem is WatchlistItem
    assert watchlist.WatchlistThesis is WatchlistThesis
    assert watchlist.WatchlistPriority is WatchlistPriority
    assert watchlist.WatchlistStatus is WatchlistStatus
    assert watchlist.WatchlistSignal is WatchlistSignal
    assert watchlist.WatchlistInsight is WatchlistInsight
    assert "WatchlistItem" in watchlist.__all__


def test_invalid_watchlist_values_are_rejected() -> None:
    """Unknown enum strings and blank required fields should fail early."""
    with pytest.raises(ValueError):
        WatchlistItem(symbol="NVDA", priority="urgent")

    with pytest.raises(ValueError):
        WatchlistItem(symbol="NVDA", status="deleted")

    with pytest.raises(ValueError):
        WatchlistThesis(symbol=" ", thesis="AI demand can compound.")

    with pytest.raises(ValueError):
        WatchlistSignal(symbol="NVDA", signal_type=" ", summary="Momentum", strength=1)
