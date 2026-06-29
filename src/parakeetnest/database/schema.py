"""Database schema initialization helpers."""

from sqlalchemy.engine import Engine

from parakeetnest.database.models import Base


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
    "recommendations",
    "reports",
)


def table_names() -> tuple[str, ...]:
    """Return the planned v1 table names."""
    return TABLES


def initialize_database(engine: Engine) -> None:
    """Create all v1 database tables."""
    Base.metadata.create_all(bind=engine)
