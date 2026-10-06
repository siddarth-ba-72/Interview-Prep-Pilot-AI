from app.models.mock_interview import Exchange, MockInterviewSession, QuestionState
from app.models.mock_interview_report import ImprovementSuggestion, MockInterviewReport
from app.schemas.base import CamelModel
from app.timeutil import UtcDateTime


class StartInterviewRequest(CamelModel):
    experience_level: str | None = None
    difficulty: str | None = None
    duration_minutes: int | None = None


class AnswerInterviewRequest(CamelModel):
    answer: str | None = None


class InterviewConfigResponse(CamelModel):
    experience_level: str | None = None
    difficulty: str | None = None
    duration_minutes: int | None = None

    @classmethod
    def from_session(cls, session: MockInterviewSession) -> "InterviewConfigResponse":
        return cls(
            experience_level=session.experience_level,
            difficulty=session.difficulty,
            duration_minutes=session.duration_minutes,
        )


class InterviewQuestionResponse(CamelModel):
    question: str | None = None
    theme: str | None = None
    is_follow_up: bool  # the frontend reads currentQuestion.isFollowUp

    @classmethod
    def from_state(cls, state: QuestionState | None) -> "InterviewQuestionResponse | None":
        if state is None:
            return None
        return cls(question=state.question, theme=state.theme, is_follow_up=state.is_follow_up)


class ThemeProgressResponse(CamelModel):
    current_theme_index: int  # 1-based position, despite the name: it is what the UI shows
    total_themes: int

    @classmethod
    def from_session(cls, session: MockInterviewSession) -> "ThemeProgressResponse":
        total = len(session.theme_plan) if session.theme_plan else 0
        current = min((session.current_theme_index or 0) + 1, max(total, 1))
        return cls(current_theme_index=current, total_themes=total)


class InterviewExchangeResponse(CamelModel):
    index: int  # 1-based
    question: str | None = None
    theme: str | None = None
    is_follow_up: bool
    user_answer: str | None = None
    rating: str | None = None
    points: int | None = None
    feedback: str | None = None

    @classmethod
    def from_exchange(cls, index: int, exchange: Exchange) -> "InterviewExchangeResponse":
        return cls(
            index=index,
            question=exchange.question,
            theme=exchange.theme,
            is_follow_up=exchange.is_follow_up,
            user_answer=exchange.user_answer,
            rating=exchange.rating,
            points=exchange.points,
            feedback=exchange.feedback,
        )

    @classmethod
    def from_exchanges(cls, exchanges: list[Exchange] | None) -> "list[InterviewExchangeResponse]":
        return [cls.from_exchange(i, e) for i, e in enumerate(exchanges or [], start=1)]


class InterviewEvaluationResponse(CamelModel):
    rating: str
    feedback: str
    points: int | None = None


class ImprovementSuggestionResponse(CamelModel):
    question: str | None = None
    user_answer: str | None = None
    theme: str | None = None
    better_answer: str | None = None

    @classmethod
    def from_suggestion(cls, s: ImprovementSuggestion) -> "ImprovementSuggestionResponse":
        return cls(question=s.question, user_answer=s.user_answer, theme=s.theme, better_answer=s.better_answer)


class InterviewReportResponse(CamelModel):
    session_id: str
    score: int | None = None
    max_score: int | None = None
    pass_threshold: int | None = None
    passed: bool
    strengths: list[str]
    weaknesses: list[str]
    improvement_suggestions: list[ImprovementSuggestionResponse]
    overall_summary: str | None = None
    config: InterviewConfigResponse | None = None
    completion_reason: str | None = None
    exchange_summary: list[InterviewExchangeResponse]
    created_at: UtcDateTime | None = None

    @classmethod
    def from_report(cls, report: MockInterviewReport) -> "InterviewReportResponse":
        return cls(
            session_id=report.mock_interview_session_id,
            score=report.score,
            max_score=report.max_score,
            pass_threshold=report.pass_threshold,
            passed=report.passed is True,
            strengths=report.strengths or [],
            weaknesses=report.weaknesses or [],
            improvement_suggestions=[
                ImprovementSuggestionResponse.from_suggestion(s) for s in report.improvement_suggestions or []
            ],
            overall_summary=report.overall_summary,
            config=InterviewConfigResponse(**report.config.model_dump()) if report.config else None,
            completion_reason=report.completion_reason,
            exchange_summary=InterviewExchangeResponse.from_exchanges(report.exchange_summary),
            created_at=report.created_at,
        )


class InterviewStartResponse(CamelModel):
    session_id: str
    deadline_at: UtcDateTime | None = None
    remaining_seconds: int
    current_question: InterviewQuestionResponse | None = None
    theme_progress: ThemeProgressResponse
    status: str
    config: InterviewConfigResponse
    exchanges: list[InterviewExchangeResponse]
    resumed: bool


class InterviewStateResponse(CamelModel):
    is_complete: bool
    session_id: str
    status: str
    deadline_at: UtcDateTime | None = None
    remaining_seconds: int
    current_question: InterviewQuestionResponse | None = None
    theme_progress: ThemeProgressResponse
    exchanges: list[InterviewExchangeResponse]
    completion_reason: str | None = None
    config: InterviewConfigResponse
    report: InterviewReportResponse | None = None


class InterviewAnswerResponse(CamelModel):
    evaluation: InterviewEvaluationResponse | None = None
    next_question: InterviewQuestionResponse | None = None
    theme_progress: ThemeProgressResponse
    exchange: InterviewExchangeResponse | None = None
    remaining_seconds: int
    is_complete: bool


class InterviewSummaryResponse(CamelModel):
    session_id: str
    status: str
    completion_reason: str | None = None
    config: InterviewConfigResponse
    score: int | None = None
    max_score: int | None = None
    passed: bool | None = None
    answered_count: int
    created_at: UtcDateTime | None = None
    completed_at: UtcDateTime | None = None
