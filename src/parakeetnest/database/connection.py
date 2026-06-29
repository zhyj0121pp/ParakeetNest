"""SQLAlchemy engine and session helpers."""

from pathlib import Path
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def sqlite_url(database_path: Path) -> str:
    """Return a SQLAlchemy SQLite URL for a local database path."""
    return f"sqlite:///{database_path}"


def create_database_engine(database_url: str, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for the configured database URL."""
    return create_engine(database_url, echo=echo, future=True)


def create_sqlite_engine(database_path: Path, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for a local SQLite database."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_database_engine(sqlite_url(database_path), echo=echo)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to an engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of database operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
