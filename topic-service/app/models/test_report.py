from datetime import datetime

from app.schemas.base import CamelModel

MAX_SCORE = 60
PASS_THRESHOLD = 36


class QuestionResult(CamelModel):
    question_id: str
    section: str
    question_text: str
    user_answer: str | None = None
    correct_answer: str | None = None
    is_correct: bool
    evaluation: str | None = None
    points_awarded: int


class TestReport(CamelModel):
    """topics_db.test_reports. `test_session_id` and `topic_id` are _id hex strings."""

    __test__ = False  # not a pytest class

    id: str | None = None
    test_session_id: str
    topic_id: str
    user_id: str
    raw_score: int
    max_score: int = MAX_SCORE
    pass_threshold: int = PASS_THRESHOLD
    passed: bool
    avg_score_at_time: float | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    question_summary: list[QuestionResult]
    attempt_number: int | None = None
    based_on_previous_attempt: bool = False
    created_at: datetime | None = None
