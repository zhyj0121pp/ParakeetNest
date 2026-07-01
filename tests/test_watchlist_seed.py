"""Tests for local watchlist seed loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistPriority,
    WatchlistStatus,
    load_watchlist_items,
)


def test_load_watchlist_items_from_valid_seed_file(tmp_path: Path) -> None:
    """A JSON seed file should load provider-neutral watchlist items."""
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text(
        """
        [
          {
            "symbol": "nvda",
            "company_name": "NVIDIA",
            "theme": "AI infrastructure",
            "reason": "Track AI accelerator demand",
            "priority": "high",
            "notes": ["Watch valuation risk"]
          }
        ]
        """,
        encoding="utf-8",
    )

    items = load_watchlist_items(seed_path)

    (item,) = items
    assert item.symbol == "NVDA"
    assert item.company_name == "NVIDIA"
    assert item.theme == "AI infrastructure"
    assert item.reason == "Track AI accelerator demand"
    assert item.priority is WatchlistPriority.HIGH
    assert item.notes == ("Watch valuation risk",)


def test_load_watchlist_items_uses_watchlist_item_defaults(
    tmp_path: Path,
) -> None:
    """Missing optional seed fields should keep WatchlistItem defaults."""
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text('[{"symbol": "amd"}]', encoding="utf-8")

    (item,) = load_watchlist_items(seed_path)

    assert item.symbol == "AMD"
    assert item.company_name is None
    assert item.theme is None
    assert item.reason is None
    assert item.priority is WatchlistPriority.MEDIUM
    assert item.status is WatchlistStatus.ACTIVE
    assert item.notes == ()


def test_load_watchlist_items_invalid_json_fails_clearly(
    tmp_path: Path,
) -> None:
    """Invalid JSON should raise a clear seed-file error."""
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text("[", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid watchlist seed JSON"):
        load_watchlist_items(seed_path)


def test_duplicate_active_seed_symbols_fail_through_repository_behavior(
    tmp_path: Path,
) -> None:
    """Duplicate active symbols should be rejected by the repository."""
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text(
        '[{"symbol": "NVDA"}, {"symbol": "nvda"}]',
        encoding="utf-8",
    )

    items = load_watchlist_items(seed_path)

    with pytest.raises(ValueError, match="active watchlist item already exists"):
        InMemoryWatchlistRepository(items)
