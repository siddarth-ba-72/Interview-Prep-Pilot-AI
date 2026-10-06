from app.errors import ApiError
from app.models.test_report import QuestionResult, TestReport
from app.models.test_session import TestSession
from app.schemas.base import CamelModel
from app.timeutil import UtcDateTime


class TestQuestionResponse(CamelModel):
    """Never carries correctOption or modelAnswer: those stay server-side until the report."""

    __test__ = False

    question_id: str
    section: str
    text: str
    options: list[str] | None = None


class TestStartResponse(CamelModel):
    __test__ = False

    session_id: str
    questions: list[TestQuestionResponse]
    attempt_number: int | None = None
    based_on_previous_attempt: bool | None = None

    @classmethod
    def from_session(cls, session: TestSession, computed_based_on_previous: bool = False) -> "TestStartResponse":
        stored = session.based_on_previous_attempt
        return cls(
            session_id=session.id,
            questions=[
                TestQuestionResponse(question_id=q.question_id, section=q.section, text=q.text, options=q.options)
                for q in session.questions
            ],
            attempt_number=session.attempt_number,
            # the stored value wins; the flag computed at start time is only a fallback
            based_on_previous_attempt=stored if stored is not None else computed_based_on_previous,
        )


class SubmitAnswerRequest(CamelModel):
    question_id: str | None = None
    user_answer: str | None = None  # null = not answered; "" counts as an answer


class SubmitTestRequest(CamelModel):
    answers: list[SubmitAnswerRequest] | None = None

    def ensure_valid(self) -> None:
        # Java threw a NullPointerException here (a 500) after burning an AI call; reject it up front instead.
        if self.answers is None:
            raise ApiError(400, "USER_INVALID_INPUT", "Answers are required")


class QuestionResultResponse(CamelModel):
    question_id: str
    section: str
    question_text: str
    user_answer: str | None = None
    correct_answer: str | None = None
    is_correct: bool
    evaluation: str | None = None
    points_awarded: int

    @classmethod
    def from_result(cls, result: QuestionResult) -> "QuestionResultResponse":
        return cls(**result.model_dump())


class TestReportResponse(CamelModel):
    __test__ = False

    test_session_id: str
    raw_score: int
    max_score: int
    pass_threshold: int
    passed: bool
    avg_score_at_time: float | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    question_summary: list[QuestionResultResponse]
    attempt_number: int | None = None
    based_on_previous_attempt: bool
    created_at: UtcDateTime | None = None

    @classmethod
    def from_report(cls, report: TestReport) -> "TestReportResponse":
        return cls(
            test_session_id=report.test_session_id,
            raw_score=report.raw_score,
            max_score=report.max_score,
            pass_threshold=report.pass_threshold,
            passed=report.passed,
            avg_score_at_time=report.avg_score_at_time,
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            question_summary=[QuestionResultResponse.from_result(r) for r in report.question_summary],
            attempt_number=report.attempt_number,
            based_on_previous_attempt=report.based_on_previous_attempt,
            created_at=report.created_at,
        )


class TestListItemResponse(CamelModel):
    __test__ = False

    session_id: str
    completed_at: UtcDateTime | None = None
    raw_score: int
    attempt_number: int | None = None
