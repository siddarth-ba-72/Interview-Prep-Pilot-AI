from datetime import datetime
from enum import StrEnum

from app.schemas.base import CamelModel


class Status(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class CompletionReason(StrEnum):
    USER_ENDED = "USER_ENDED"
    TIME_EXPIRED = "TIME_EXPIRED"
    COMPLETED_NATURALLY = "COMPLETED_NATURALLY"


class Rating(StrEnum):
    STRONG = "STRONG"
    SATISFACTORY = "SATISFACTORY"
    WEAK = "WEAK"


class QuestionState(CamelModel):
    question: str | None = None
    theme: str | None = None
    is_follow_up: bool = False


class Exchange(CamelModel):
    question: str | None = None
    theme: str | None = None
    is_follow_up: bool = False
    user_answer: str | None = None
    rating: Rating | None = None
    points: int | None = None
    feedback: str | None = None


class MockInterviewSession(CamelModel):
    """topics_db.mock_interview_sessions. `topic_id` is the topic's _id hex, not its publicId."""

    id: str | None = None
    topic_id: str
    user_id: str
    status: Status = Status.IN_PROGRESS
    completion_reason: CompletionReason | None = None
    experience_level: str | None = None
    difficulty: str | None = None
    duration_minutes: int | None = None
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    theme_plan: list[str] | None = None
    current_theme_index: int | None = 0
    current_follow_up_count: int | None = 0
    current_question: QuestionState | None = None
    exchanges: list[Exchange] | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
