"""Database schema initialization helpers."""

from sqlalchemy.engine import Engine

from parakeetnest.database.migrations import run_migrations


TABLES: tuple[str, ...] = (
    "holdings",
    "watchlist_items",
    "market_data",
    "financial_data",
    "news_items",
    "macro_data",
    "calendar_events",
    "data_quality_reports",
    "investment_theses",
    "committee_discussions",
    "committee_meeting",
    "committee_meeting_message",
    "committee_memories",
    "recommendations",
    "reports",
)


def table_names() -> tuple[str, ...]:
    """Return the planned v1 table names."""
    return TABLES


def initialize_database(engine: Engine) -> None:
    """Create all v1 database tables."""
    run_migrations(engine)
