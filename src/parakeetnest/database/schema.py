"""SQLite schema placeholders."""


TABLES: tuple[str, ...] = (
    "holdings",
    "market_data",
    "financials",
    "macro",
    "calendar",
    "news",
    "reports",
)


def table_names() -> tuple[str, ...]:
    """Return the planned v1 SQLite table names."""
    return TABLES
