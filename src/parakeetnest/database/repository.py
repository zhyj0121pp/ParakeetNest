"""Repository helpers for SQLAlchemy-backed persistence."""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from parakeetnest.committee.models import MeetingStatus
from parakeetnest.database.models import Base, CommitteeMeeting, CommitteeMeetingMessage


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


class CommitteeMeetingRepository:
    """DAO for persistent AI committee meetings and messages."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a SQLAlchemy session."""
        self.session = session

    def create_meeting(self, question: str, ticker: str) -> CommitteeMeeting:
        """Create a pending committee meeting."""
        meeting = CommitteeMeeting(
            question=question,
            ticker=ticker,
            status=MeetingStatus.PENDING.value,
        )
        self.session.add(meeting)
        self.session.flush()
        self.session.refresh(meeting)
        return meeting

    def update_meeting_completed(
        self,
        meeting_id: int,
        result_json: dict[str, object],
    ) -> CommitteeMeeting:
        """Mark a meeting completed and store the final JSON result."""
        meeting = self._require_meeting(meeting_id)
        meeting.status = MeetingStatus.COMPLETED.value
        meeting.result_json = result_json
        meeting.error_message = None
        self.session.flush()
        self.session.refresh(meeting)
        return meeting

    def update_meeting_failed(self, meeting_id: int, error_message: str) -> CommitteeMeeting:
        """Mark a meeting failed and store the error message."""
        meeting = self._require_meeting(meeting_id)
        meeting.status = MeetingStatus.FAILED.value
        meeting.error_message = error_message
        meeting.result_json = None
        self.session.flush()
        self.session.refresh(meeting)
        return meeting

    def insert_meeting_message(
        self,
        meeting_id: int,
        agent_name: str,
        role: str,
        content: str,
    ) -> CommitteeMeetingMessage:
        """Persist one agent message for a meeting."""
        self._require_meeting(meeting_id)
        message = CommitteeMeetingMessage(
            meeting_id=meeting_id,
            agent_name=agent_name,
            role=role,
            content=content,
        )
        self.session.add(message)
        self.session.flush()
        self.session.refresh(message)
        return message

    def list_meeting_messages(self, meeting_id: int) -> Sequence[CommitteeMeetingMessage]:
        """List meeting messages in insertion order."""
        statement = (
            select(CommitteeMeetingMessage)
            .where(CommitteeMeetingMessage.meeting_id == meeting_id)
            .order_by(CommitteeMeetingMessage.id)
        )
        return self.session.scalars(statement).all()

    def _require_meeting(self, meeting_id: int) -> CommitteeMeeting:
        meeting = self.session.get(CommitteeMeeting, meeting_id)
        if meeting is None:
            raise ValueError(f"Committee meeting {meeting_id} does not exist.")
        return meeting
