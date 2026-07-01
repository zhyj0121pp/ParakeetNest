"""Local JSON seed loading for watchlist items."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parakeetnest.watchlist.models import WatchlistItem


class WatchlistSeedLoader:
    """Load provider-neutral watchlist items from a local JSON seed file."""

    def load(self, path: Path) -> tuple[WatchlistItem, ...]:
        """Load watchlist items from a JSON file."""
        return load_watchlist_items(path)


def load_watchlist_items(path: Path) -> tuple[WatchlistItem, ...]:
    """Load watchlist items from a simple local JSON seed file."""
    try:
        raw_items = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid watchlist seed JSON in {path}: {error.msg}"
        ) from error

    if not isinstance(raw_items, list):
        raise ValueError(f"watchlist seed file must contain a JSON array: {path}")

    items: list[WatchlistItem] = []
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise ValueError(
                f"watchlist seed item at index {index} must be a JSON object"
            )
        items.append(_build_watchlist_item(raw_item, index))
    return tuple(items)


def _build_watchlist_item(raw_item: dict[str, Any], index: int) -> WatchlistItem:
    try:
        return WatchlistItem(**raw_item)
    except TypeError as error:
        raise ValueError(
            f"invalid watchlist seed item at index {index}: {error}"
        ) from error
    except ValueError as error:
        raise ValueError(
            f"invalid watchlist seed item at index {index}: {error}"
        ) from error


__all__ = ["WatchlistSeedLoader", "load_watchlist_items"]
