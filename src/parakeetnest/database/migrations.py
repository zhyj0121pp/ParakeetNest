"""Lightweight SQLite migration runner for ParakeetNest v1."""

from sqlalchemy.engine import Engine

from parakeetnest.database.models import Base


def run_migrations(engine: Engine) -> None:
    """Apply all currently defined v1 schema migrations."""
    Base.metadata.create_all(bind=engine)
