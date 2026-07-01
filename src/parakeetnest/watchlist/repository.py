"""Repository abstractions for provider-neutral watchlist items.

This module defines the watchlist repository boundary without introducing
persistence, external providers, LLM calls, committee integration, or CLI
behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace

from parakeetnest.watchlist.models import WatchlistItem, WatchlistStatus


class WatchlistRepository(ABC):
    """Abstract repository interface for watchlist items."""

    @abstractmethod
    def list_items(self) -> tuple[WatchlistItem, ...]:
        """Return watchlist items in deterministic symbol order."""

    @abstractmethod
    def get_item(self, symbol: str) -> WatchlistItem | None:
        """Return one watchlist item by symbol, if it exists."""

    @abstractmethod
    def add_item(self, item: WatchlistItem) -> WatchlistItem:
        """Add a watchlist item and return the saved item."""

    @abstractmethod
    def update_item(self, item: WatchlistItem) -> WatchlistItem:
        """Update an existing watchlist item and return the saved item."""

    @abstractmethod
    def archive_item(self, symbol: str) -> WatchlistItem:
        """Mark a watchlist item archived and return the saved item."""


class InMemoryWatchlistRepository(WatchlistRepository):
    """Concrete in-memory repository for watchlist items."""

    def __init__(self, items: tuple[WatchlistItem, ...] = ()) -> None:
        self._items: dict[str, WatchlistItem] = {}
        for item in items:
            self.add_item(item)

    def list_items(self) -> tuple[WatchlistItem, ...]:
        """Return watchlist items in deterministic symbol order."""
        return tuple(self._items[symbol] for symbol in sorted(self._items))

    def get_item(self, symbol: str) -> WatchlistItem | None:
        """Return one watchlist item by symbol, if present."""
        return self._items.get(normalize_watchlist_symbol(symbol))

    def add_item(self, item: WatchlistItem) -> WatchlistItem:
        """Add a watchlist item unless an active item already uses its symbol."""
        existing = self._items.get(item.symbol)
        if (
            existing is not None
            and existing.status is WatchlistStatus.ACTIVE
            and item.status is WatchlistStatus.ACTIVE
        ):
            raise ValueError(f"active watchlist item already exists for {item.symbol}")
        self._items[item.symbol] = item
        return item

    def update_item(self, item: WatchlistItem) -> WatchlistItem:
        """Update an existing watchlist item."""
        if item.symbol not in self._items:
            raise ValueError(f"watchlist item does not exist for {item.symbol}")
        self._items[item.symbol] = item
        return item

    def archive_item(self, symbol: str) -> WatchlistItem:
        """Mark a watchlist item archived without deleting it."""
        normalized = normalize_watchlist_symbol(symbol)
        item = self._items.get(normalized)
        if item is None:
            raise ValueError(f"watchlist item does not exist for {normalized}")
        archived = replace(item, status=WatchlistStatus.ARCHIVED)
        self._items[normalized] = archived
        return archived


def normalize_watchlist_symbol(symbol: str) -> str:
    """Normalize a symbol using the WatchlistItem domain rules."""
    return WatchlistItem(symbol=symbol).symbol


__all__ = [
    "InMemoryWatchlistRepository",
    "WatchlistRepository",
    "normalize_watchlist_symbol",
]
