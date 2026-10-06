from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.base import CamelModel


class Status(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Section(StrEnum):
    MCQ = "MCQ"
    SUBJECTIVE = "SUBJECTIVE"


class Question(CamelModel):
    question_id: str
    section: Section
    text: str
    options: list[str] | None = None  # MCQ only
    correct_option: str | None = None  # server-side only, never sent to the client
    model_answer: str | None = None  # SUBJECTIVE only, never sent to the client


class Answer(CamelModel):
    question_id: str
    user_answer: str | None = None  # None means not answered; "" is an answer
    is_correct: bool
    evaluation: str | None = None
    points_awarded: int


class TestSession(CamelModel):
    """topics_db.test_sessions. `topic_id` is the topic's _id hex, not its publicId."""

    __test__ = False  # not a pytest class

    id: str | None = None
    topic_id: str
    user_id: str
    status: Status = Status.IN_PROGRESS
    questions: list[Question] = Field(default_factory=list)
    answers: list[Answer] | None = None
    raw_score: int | None = None
    attempt_number: int | None = None
    based_on_previous_attempt: bool | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
