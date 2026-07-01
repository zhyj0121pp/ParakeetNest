"""Repository contract for committee memory.

This module defines the persistence boundary for committee memory without
choosing a storage backend or retrieval strategy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from parakeetnest.committee.memory.models import (
    CommitteeMemory,
    MemoryQuery,
    MemorySearchResult,
)


class CommitteeMemoryRepository(ABC):
    """Abstract repository interface for durable committee memory."""

    @abstractmethod
    def save(self, memory: CommitteeMemory) -> CommitteeMemory:
        """Persist a committee memory and return the saved record."""

    @abstractmethod
    def get(self, memory_id: str) -> CommitteeMemory | None:
        """Return one committee memory by identifier, if it exists."""

    @abstractmethod
    def search(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        """Return ranked committee memories matching a query."""

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete one committee memory by identifier."""

    @abstractmethod
    def list_recent(self, limit: int = 20) -> tuple[CommitteeMemory, ...]:
        """Return recently saved committee memories."""


def validate_memory_id(memory_id: str) -> str:
    """Normalize and validate a repository memory identifier."""
    normalized = str(memory_id).strip()
    if not normalized:
        raise ValueError("memory_id cannot be blank")
    return normalized


def validate_positive_limit(limit: int) -> int:
    """Validate a positive result limit."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    return limit
