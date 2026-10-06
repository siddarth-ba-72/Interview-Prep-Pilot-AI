"""In-memory stand-ins for the Mock Interview repositories and AI client."""
from datetime import datetime, timedelta

from app.clients.ai_schemas import (
    AiImprovementSuggestion,
    GenerateInterviewReportResponse,
    NextTurnEvaluation,
    NextTurnNext,
    NextTurnRequest,
    NextTurnResponse,
    PlanInterviewResponse,
    ReportExchange,
)
from app.models.mock_interview import Exchange, MockInterviewSession, QuestionState
from app.models.mock_interview_report import MockInterviewReport
from app.timeutil import utc_now
from tests.unit.fakes import FakeTopics


class FakeInterviewSessions:
    def __init__(self) -> None:
        self.items: dict[str, MockInterviewSession] = {}
        self.saves = 0

    async def find_by_id(self, session_id: str) -> MockInterviewSession | None:
        return self.items.get(session_id)

    async def find_in_progress(self, topic_id: str, user_id: str) -> MockInterviewSession | None:
        return next(
            (s for s in self.items.values()
             if s.topic_id == topic_id and s.user_id == user_id and s.status == "IN_PROGRESS"),
            None,
        )

    async def find_by_topic_and_user(self, topic_id: str, user_id: str) -> list[MockInterviewSession]:
        return [s for s in self.items.values() if s.topic_id == topic_id and s.user_id == user_id]

    async def insert(self, session: MockInterviewSession) -> MockInterviewSession:
        session.id = session.id or f"{len(self.items) + 1:024x}"
        session.created_at = session.created_at or utc_now()
        self.items[session.id] = session
        return session

    async def save(self, session: MockInterviewSession) -> MockInterviewSession:
        self.saves += 1
        if session.id is None:
            return await self.insert(session)
        self.items[session.id] = session
        return session


class FakeInterviewReports:
    def __init__(self) -> None:
        self.items: list[MockInterviewReport] = []
        self.batch_calls = 0

    async def find_by_session_id(self, session_id: str) -> MockInterviewReport | None:
        return next((r for r in self.items if r.mock_interview_session_id == session_id), None)

    async def find_by_session_ids(self, session_ids: list[str]) -> dict[str, MockInterviewReport]:
        self.batch_calls += 1
        found: dict[str, MockInterviewReport] = {}
        for report in self.items:
            if report.mock_interview_session_id in session_ids:
                found.setdefault(report.mock_interview_session_id, report)
        return found

    async def insert(self, report: MockInterviewReport) -> MockInterviewReport:
        report.id = f"{len(self.items) + 1:024x}"
        report.created_at = utc_now()
        self.items.append(report)
        return report


class FakeInterviewAi:
    """Scripted plan / next-turn / report. An unstubbed next_turn returns None, like an unstubbed Mockito mock."""

    def __init__(self) -> None:
        self.plan_result: PlanInterviewResponse | None = None
        self.plan_error: Exception | None = None
        self.turn_result: NextTurnResponse | None = None
        self.turn_error: Exception | None = None
        self.report_result: GenerateInterviewReportResponse | None = None
        self.report_error: Exception | None = None
        self.plan_calls: list[tuple] = []
        self.turn_requests: list[NextTurnRequest] = []
        self.report_calls: list[tuple] = []

    async def plan_interview(self, topic_name, experience_level, difficulty, duration_minutes):
        self.plan_calls.append((topic_name, experience_level, difficulty, duration_minutes))
        if self.plan_error:
            raise self.plan_error
        return self.plan_result

    async def next_turn(self, request: NextTurnRequest):
        self.turn_requests.append(request)
        if self.turn_error:
            raise self.turn_error
        return self.turn_result

    async def generate_interview_report(
        self, topic_name, experience_level, difficulty, exchanges: list[ReportExchange]
    ):
        self.report_calls.append((topic_name, experience_level, difficulty, exchanges))
        if self.report_error:
            raise self.report_error
        return self.report_result


def turn(rating: str | None, question: str | None, theme: str | None, follow_up: bool, advance: bool,
         feedback: str | None = "feedback") -> NextTurnResponse:
    return NextTurnResponse(
        evaluation=NextTurnEvaluation(rating=rating, feedback=feedback),
        next=NextTurnNext(question=question, theme=theme, is_follow_up=follow_up, advance_theme=advance),
    )


def report_response(summary="A summary.", strengths=("s",), weaknesses=("w",), suggestions=()):
    return GenerateInterviewReportResponse(
        strengths=list(strengths),
        weaknesses=list(weaknesses),
        overall_summary=summary,
        improvement_suggestions=[
            AiImprovementSuggestion(question=q, user_answer=a, theme=t, better_answer=b) for q, a, t, b in suggestions
        ],
    )


class Clock:
    """A clock the tests can move."""

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or utc_now()

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


class Interviews:
    """The service with fakes wired in, mirroring the Java test's setUp()."""

    def __init__(self, clock: Clock | None = None) -> None:
        from app.models.topic import Topic
        from app.services.mock_interview_service import MockInterviewService

        self.clock = clock or Clock()
        self.topics = FakeTopics()
        self.topic = Topic(id="topic-1", public_id="topic-1", user_id="user-1", name="Spring Boot")
        self.topics.items["topic-1"] = self.topic
        self.sessions = FakeInterviewSessions()
        self.reports = FakeInterviewReports()
        self.ai = FakeInterviewAi()
        self.service = MockInterviewService(self.topics, self.sessions, self.reports, self.ai, clock=self.clock)

    def in_progress_session(self, question: str, theme: str) -> MockInterviewSession:
        """Same as the Java helper: SENIOR/MEDIUM/30, deadline in 20 minutes, two themes."""
        now = self.clock()
        session = MockInterviewSession(
            id="session-1",
            topic_id="topic-1",
            user_id="user-1",
            experience_level="SENIOR",
            difficulty="MEDIUM",
            duration_minutes=30,
            started_at=now,
            deadline_at=now + timedelta(minutes=20),
            theme_plan=["Core IoC & Beans", "Auto-configuration"],
            current_question=QuestionState(question=question, theme=theme, is_follow_up=False),
            exchanges=[],
            created_at=now,
        )
        self.sessions.items[session.id] = session
        return session


def exchange(question="q", theme="t", follow_up=False, answer="a", rating="STRONG", points=100, feedback="f"):
    return Exchange(question=question, theme=theme, is_follow_up=follow_up, user_answer=answer, rating=rating,
                    points=points, feedback=feedback)
