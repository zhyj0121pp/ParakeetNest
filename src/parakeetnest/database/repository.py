"""Repository helpers for SQLAlchemy-backed persistence."""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from parakeetnest.database.models import Base


ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """Small generic repository with basic create, get, and list methods."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        """Initialize the repository with a session and ORM model."""
        self.session = session
        self.model = model

    def create(self, instance: ModelT) -> ModelT:
        """Persist an ORM instance and return it with generated fields populated."""
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def get(self, record_id: int) -> ModelT | None:
        """Return one record by primary key."""
        return self.session.get(self.model, record_id)

    def list(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Return records ordered by primary key."""
        statement = select(self.model).order_by(self.model.id).offset(offset).limit(limit)
        return self.session.scalars(statement).all()
