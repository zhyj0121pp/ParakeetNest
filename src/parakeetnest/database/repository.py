"""Base repository skeleton for SQLite-backed persistence."""

import sqlite3


class SQLiteRepository:
    """Base class for repositories using SQLite connections."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize the repository with an existing connection."""
        self.connection = connection
