from datetime import datetime

from app.models.mock_interview import Exchange
from app.schemas.base import CamelModel

MAX_SCORE = 100
PASS_THRESHOLD = 75


class ImprovementSuggestion(CamelModel):
    question: str | None = None
    user_answer: str | None = None
    theme: str | None = None
    better_answer: str | None = None


class Config(CamelModel):
    experience_level: str | None = None
    difficulty: str | None = None
    duration_minutes: int | None = None


class MockInterviewReport(CamelModel):
    """topics_db.mock_interview_reports. `mock_interview_session_id` and `topic_id` are _id hex strings."""

    id: str | None = None
    mock_interview_session_id: str
    topic_id: str
    user_id: str
    score: int | None = None
    max_score: int | None = MAX_SCORE
    pass_threshold: int | None = PASS_THRESHOLD
    passed: bool | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    improvement_suggestions: list[ImprovementSuggestion] | None = None
    overall_summary: str | None = None
    config: Config | None = None
    completion_reason: str | None = None
    exchange_summary: list[Exchange] | None = None
    created_at: datetime | None = None
