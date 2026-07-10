"""Provider-agnostic News Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class NewsArticle:
    """Normalized news item from any provider."""

    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None
    symbols: list[str] | None = None
    provider: str | None = None

    def __post_init__(self) -> None:
        """Normalize optional symbols for stable filtering."""
        if self.symbols is not None:
            symbols = [symbol.strip().upper() for symbol in self.symbols if symbol.strip()]
            object.__setattr__(self, "symbols", symbols)


@dataclass(frozen=True)
class NewsQuery:
    """Provider-neutral news search request."""

    symbols: list[str] | None = None
    keywords: list[str] | None = None
    limit: int = 10
    published_after: datetime | None = None
    published_before: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize query fields used by providers."""
        if self.limit < 1:
            raise ValueError("limit must be at least 1")

        if self.symbols is not None:
            symbols = [symbol.strip().upper() for symbol in self.symbols if symbol.strip()]
            object.__setattr__(self, "symbols", symbols)

        if self.keywords is not None:
            keywords = [keyword.strip() for keyword in self.keywords if keyword.strip()]
            object.__setattr__(self, "keywords", keywords)

        for field_name in ("published_after", "published_before"):
            value = getattr(self, field_name)
            if value is not None and value.tzinfo is None:
                object.__setattr__(self, field_name, value.replace(tzinfo=UTC))
        if (
            self.published_after is not None
            and self.published_before is not None
            and self.published_after > self.published_before
        ):
            raise ValueError("published_after must not be after published_before")


__all__ = ["NewsArticle", "NewsQuery"]
