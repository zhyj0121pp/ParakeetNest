"""Tests for provider-neutral watchlist repositories."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistItem,
    WatchlistPriority,
    WatchlistStatus,
)


CREATED_AT = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)


def _item(
    symbol: str,
    *,
    company_name: str | None = None,
    priority: WatchlistPriority = WatchlistPriority.MEDIUM,
    status: WatchlistStatus = WatchlistStatus.ACTIVE,
) -> WatchlistItem:
    return WatchlistItem(
        symbol=symbol,
        company_name=company_name,
        priority=priority,
        status=status,
        created_at=CREATED_AT,
    )


def test_add_and_retrieve_item() -> None:
    repository = InMemoryWatchlistRepository()
    item = _item(" nvda ", company_name="NVIDIA")

    saved = repository.add_item(item)

    assert saved == item
    assert repository.get_item("nvda") == item


def test_add_rejects_duplicate_active_symbol() -> None:
    repository = InMemoryWatchlistRepository()
    repository.add_item(_item("NVDA"))

    with pytest.raises(ValueError, match="active watchlist item already exists"):
        repository.add_item(_item(" nvda "))


def test_get_missing_item_returns_none() -> None:
    repository = InMemoryWatchlistRepository()

    assert repository.get_item("MSFT") is None


def test_update_existing_item() -> None:
    repository = InMemoryWatchlistRepository()
    original = _item("NVDA", priority=WatchlistPriority.LOW)
    updated = _item(
        "nvda",
        company_name="NVIDIA Corporation",
        priority=WatchlistPriority.HIGH,
    )
    repository.add_item(original)

    saved = repository.update_item(updated)

    assert saved == updated
    assert repository.get_item("NVDA") == updated


def test_update_missing_item_fails() -> None:
    repository = InMemoryWatchlistRepository()

    with pytest.raises(ValueError, match="watchlist item does not exist"):
        repository.update_item(_item("AMD"))


def test_archive_item_marks_item_archived_without_deleting() -> None:
    repository = InMemoryWatchlistRepository()
    item = _item("MSFT")
    repository.add_item(item)

    archived = repository.archive_item(" msft ")

    assert archived.status is WatchlistStatus.ARCHIVED
    assert repository.get_item("MSFT") == archived
    assert repository.list_items() == (archived,)


def test_list_items_order_is_deterministic_by_symbol() -> None:
    repository = InMemoryWatchlistRepository()
    msft = _item("MSFT")
    aapl = _item("AAPL")
    nvda = _item("NVDA")

    repository.add_item(msft)
    repository.add_item(aapl)
    repository.add_item(nvda)

    assert repository.list_items() == (aapl, msft, nvda)


def test_returned_collection_cannot_mutate_internal_repository_state() -> None:
    repository = InMemoryWatchlistRepository()
    aapl = _item("AAPL")
    msft = _item("MSFT")
    repository.add_item(aapl)
    repository.add_item(msft)

    listed = repository.list_items()

    assert listed == (aapl, msft)
    assert not hasattr(listed, "append")
    listed += (_item("ZZZ"),)
    assert repository.list_items() == (aapl, msft)
