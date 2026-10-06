import asyncio
import logging
import math
import weakref
from collections.abc import Callable
from datetime import datetime, timedelta

from app.clients.ai_client import AiClient
from app.clients.ai_schemas import (
    GenerateInterviewReportResponse,
    NextTurnExchange,
    NextTurnQuestionContext,
    NextTurnRequest,
    NextTurnResponse,
    ReportExchange,
)
from app.errors import ErrorCode, api_error, mock_interview_not_found, topic_not_found
from app.models.mock_interview import (
    CompletionReason,
    Exchange,
    MockInterviewSession,
    QuestionState,
    Rating,
    Status,
)
from app.models.mock_interview_report import (
    MAX_SCORE,
    PASS_THRESHOLD,
    Config,
    ImprovementSuggestion,
    MockInterviewReport,
)
from app.models.topic import Topic
from app.repositories.mock_interview_reports import MockInterviewReportsRepository
from app.repositories.mock_interview_sessions import MockInterviewSessionsRepository
from app.repositories.topics import TopicsRepository
from app.schemas.interviews import (
    AnswerInterviewRequest,
    InterviewAnswerResponse,
    InterviewConfigResponse,
    InterviewEvaluationResponse,
    InterviewExchangeResponse,
    InterviewQuestionResponse,
    InterviewReportResponse,
    InterviewStartResponse,
    InterviewStateResponse,
    InterviewSummaryResponse,
    StartInterviewRequest,
    ThemeProgressResponse,
)
from app.timeutil import utc_now

logger = logging.getLogger(__name__)

# Hard cap on follow-ups within one theme. Enforced here, not by the AI.
MAX_FOLLOW_UPS_PER_THEME = 4
ANSWER_GRACE = timedelta(seconds=5)  # absorbs network latency; beyond it the answer is not recorded

# Listed in the order the Java code declared them. (Java printed a Set.of(...), whose order varies per JVM run.)
ALLOWED_EXPERIENCE_LEVELS = ("JUNIOR", "INTERMEDIATE", "SENIOR", "MASTER", "ADVANCED")
ALLOWED_DIFFICULTIES = ("EASY", "MEDIUM", "HARD")
ALLOWED_DURATIONS = (30, 45, 60)

POINTS = {Rating.STRONG: 100, Rating.SATISFACTORY: 60, Rating.WEAK: 20}

# Rotated rather than reused, so a run of AI failures doesn't show the candidate the same sentence over and
# over: the symptom that reads as "stuck".
FALLBACK_QUESTION_TEMPLATES = (
    "Let's move on to {}. What are the most important things to get right there, and where do people usually go "
    "wrong?",
    "Thinking about {}: describe how you would approach it in a real project, and what you would watch out for.",
    "How would you explain {} to a teammate who has never worked with it, and what caveat would you flag for them?",
    "What trade-offs would you weigh when applying {} in a production system, and how would you decide?",
)

BLANK_ANSWER_FEEDBACK = "No answer was submitted for this question, so it scores zero."
UNSCORED_FEEDBACK = "We couldn't score this answer automatically, but it has been recorded."
DEFAULT_FEEDBACK = "This answer was recorded."


# ---------------------------------------------------------------- pure helpers

def has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def first_text(preferred: str | None, fallback: str | None) -> str | None:
    return preferred if has_text(preferred) else fallback


def index_of_ignore_case(values: list[str], candidate: str | None) -> int:
    if not has_text(candidate):
        return -1
    wanted = candidate.strip().lower()
    for i, value in enumerate(values):
        if value is not None and value.lower() == wanted:
            return i
    return -1


def dedupe_themes(themes: list[str] | None) -> list[str]:
    """Trim, drop blanks, drop case-insensitive duplicates, keeping the first occurrence."""
    seen: set[str] = set()
    result: list[str] = []
    for theme in themes or []:
        if not has_text(theme):
            continue
        trimmed = theme.strip()
        if trimmed.lower() not in seen:
            seen.add(trimmed.lower())
            result.append(trimmed)
    return result


def default_theme_plan(topic_name: str, duration_minutes: int | None) -> list[str]:
    plan = [
        f"{topic_name} fundamentals",
        f"{topic_name} in practice",
        f"Design and trade-offs in {topic_name}",
        f"Debugging and testing {topic_name}",
    ]
    if duration_minutes is not None and duration_minutes >= 45:
        plan += [f"Performance and scaling with {topic_name}", f"Real-world {topic_name} scenarios"]
    if duration_minutes is not None and duration_minutes >= 60:
        plan += [f"Advanced {topic_name} internals", f"Ecosystem and tooling around {topic_name}"]
    return plan


def parse_rating(rating: str | None) -> Rating:
    if rating is None:
        return Rating.SATISFACTORY
    try:
        return Rating(rating.strip().upper())
    except ValueError:
        return Rating.SATISFACTORY


def points_for_rating(rating: Rating | None) -> int:
    """None is a blank (or timed-out) answer, which always scores zero."""
    return 0 if rating is None else POINTS[rating]


def remaining_seconds(deadline_at: datetime | None, now: datetime) -> int:
    if deadline_at is None:
        return 0
    return max(0, int((deadline_at - now).total_seconds()))  # int() truncates toward zero, like ChronoUnit.between


def calculate_score(exchanges: list[Exchange] | None) -> int:
    """Mean of the exchange points, rounded half-up like Java's Math.round.

    Not Python's round(): that rounds half to even, so a mean of 2.5 would score 2 instead of 3.
    """
    if not exchanges:
        return 0
    total = sum(e.points or 0 for e in exchanges)
    return math.floor(total / len(exchanges) + 0.5)


def default_summary(session: MockInterviewSession) -> str:
    answered = len(session.exchanges or [])
    if answered == 0:
        return (
            "This interview ended before any questions were answered, so there is nothing to assess yet. "
            "Start a new interview when you're ready."
        )
    return (
        f"You answered {answered} question{'' if answered == 1 else 's'}. A detailed written assessment could not "
        "be generated this time, but your per-question ratings and feedback below are complete."
    )


def apply_theme_transition(
    session: MockInterviewSession, advance_theme: bool, next_theme: str | None, topic_name: str
) -> str | None:
    """Move the session onto the theme the next question belongs to; return that theme's canonical label.

    Growing the plan when the AI invents an adjacent theme keeps the progress indicator honest, and never
    moving the index backwards keeps the follow-up cap from being undone by an AI that wants to stay put.
    """
    plan = list(session.theme_plan or [])
    theme_index = session.current_theme_index or 0

    if advance_theme:
        target = theme_index + 1
        matching = index_of_ignore_case(plan, next_theme)
        if matching >= target:
            theme_index = matching  # the AI skipped ahead in the plan: follow it
        elif target >= len(plan):
            # Plan exhausted: adopt the adjacent theme the AI invented so the plan keeps growing.
            plan.append(f"More on {topic_name}" if matching >= 0 or not has_text(next_theme) else next_theme)
            theme_index = len(plan) - 1
        else:
            theme_index = target  # normal step down the plan
        session.current_follow_up_count = 0
    else:
        session.current_follow_up_count = (session.current_follow_up_count or 0) + 1

    theme_index = min(theme_index, max(0, len(plan) - 1))
    session.theme_plan = plan
    session.current_theme_index = theme_index
    return plan[theme_index] if plan else first_text(next_theme, topic_name)


def fallback_next_question(session: MockInterviewSession, topic_name: str) -> QuestionState:
    """Deterministic next question for when the AI call failed. Rotates through the templates."""
    plan = session.theme_plan
    next_index = (session.current_theme_index or 0) + 1
    theme = plan[next_index] if plan and next_index < len(plan) else f"advanced {topic_name} topics"
    rotation = len(session.exchanges or [])
    template = FALLBACK_QUESTION_TEMPLATES[rotation % len(FALLBACK_QUESTION_TEMPLATES)]
    return QuestionState(question=template.format(theme), theme=theme, is_follow_up=False)


def require_enum(value: str | None, allowed: tuple[str, ...], field: str) -> str:
    normalized = (value or "").strip().upper()
    if normalized not in allowed:
        raise api_error(ErrorCode.INVALID_INTERVIEW_CONFIG, f"{field} must be one of [{', '.join(allowed)}]")
    return normalized


def ai_next_question(response: NextTurnResponse | None) -> QuestionState | None:
    if response is None or response.next is None or not has_text(response.next.question):
        return None
    return QuestionState(question=response.next.question, theme=response.next.theme, is_follow_up=False)


# ---------------------------------------------------------------- the service

class MockInterviewService:
    def __init__(
        self,
        topics: TopicsRepository,
        sessions: MockInterviewSessionsRepository,
        reports: MockInterviewReportsRepository,
        ai: AiClient,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.topics = topics
        self.sessions = sessions
        self.reports = reports
        self.ai = ai
        self.clock = clock  # injectable so tests can move time instead of waiting for it
        # One report per session even when two requests ask for it at once (e.g. "end" racing a poll).
        self._report_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    # ------------------------------------------------------------ lookups

    async def _require_topic(self, user_id: str, topic_id: str) -> Topic:
        topic = await self.topics.find_by_public_id_and_user(topic_id, user_id)
        if topic is None:
            raise topic_not_found(topic_id)
        return topic

    async def _require_session(
        self, user_id: str, topic_id: str, session_id: str
    ) -> tuple[Topic, MockInterviewSession]:
        topic = await self._require_topic(user_id, topic_id)
        session = await self.sessions.find_by_id(session_id)  # a malformed id is just "not found"
        if session is None or session.user_id != user_id or session.topic_id != topic.id:
            raise mock_interview_not_found(session_id)
        return topic, session

    # ------------------------------------------------------------ start / resume

    async def start(
        self, user_id: str, topic_id: str, request: StartInterviewRequest | None
    ) -> InterviewStartResponse:
        request = request or StartInterviewRequest()
        topic = await self._require_topic(user_id, topic_id)

        existing = await self.sessions.find_in_progress(topic.id, user_id)
        if existing is not None:
            if self.clock() < existing.deadline_at:
                # Resume: the config in this request is deliberately ignored.
                return self._start_response(existing, resumed=True)
            # The deadline passed while the user was away: finalize it before starting a fresh one.
            await self._finalize(existing, CompletionReason.TIME_EXPIRED)

        experience_level = require_enum(request.experience_level, ALLOWED_EXPERIENCE_LEVELS, "experienceLevel")
        difficulty = require_enum(request.difficulty, ALLOWED_DIFFICULTIES, "difficulty")
        if request.duration_minutes not in ALLOWED_DURATIONS:
            raise api_error(ErrorCode.INVALID_INTERVIEW_CONFIG, "durationMinutes must be one of 30, 45, or 60")

        now = self.clock()
        session = MockInterviewSession(
            topic_id=topic.id,
            user_id=user_id,
            status=Status.IN_PROGRESS,
            experience_level=experience_level,
            difficulty=difficulty,
            duration_minutes=request.duration_minutes,
            started_at=now,
            deadline_at=now + timedelta(minutes=request.duration_minutes),
            exchanges=[],
        )
        session.theme_plan = await self._plan_themes(topic.name, session)
        session.current_question = await self._opening_question(topic.name, session)
        await self.sessions.insert(session)
        return self._start_response(session, resumed=False)

    async def _plan_themes(self, topic_name: str, session: MockInterviewSession) -> list[str]:
        try:
            plan = await self.ai.plan_interview(
                topic_name, session.experience_level, session.difficulty, session.duration_minutes
            )
            themes = dedupe_themes(plan.themes)
            if themes:
                return themes
            logger.warning("AI returned an empty theme plan; using the default plan", extra={"topic": topic_name})
        except Exception:
            logger.warning("Theme planning failed; using the default plan", exc_info=True, extra={"topic": topic_name})
        return default_theme_plan(topic_name, session.duration_minutes)

    async def _opening_question(self, topic_name: str, session: MockInterviewSession) -> QuestionState:
        first_theme = session.theme_plan[0]
        try:
            first_turn = await self.ai.next_turn(
                NextTurnRequest(
                    topic_name=topic_name,
                    experience_level=session.experience_level,
                    difficulty=session.difficulty,
                    theme_plan=session.theme_plan,
                    current_theme_index=0,
                    current_follow_up_count=0,
                    remaining_seconds=session.duration_minutes * 60,
                    prior_exchanges=[],
                    last_answer=None,
                    current_question=None,
                    must_advance_theme=False,
                    max_follow_ups=MAX_FOLLOW_UPS_PER_THEME,
                )
            )
            if first_turn.next is not None and has_text(first_turn.next.question):
                return QuestionState(
                    question=first_turn.next.question,
                    theme=first_text(first_turn.next.theme, first_theme),
                    is_follow_up=False,
                )
            logger.warning("AI returned no opening question; using the fallback opener", extra={"topic": topic_name})
        except Exception:
            logger.warning("Opening question failed; using the fallback opener", exc_info=True,
                           extra={"topic": topic_name})
        return QuestionState(
            question=f"To get started, tell me about your experience with {first_theme} "
            "and how you have applied it in practice.",
            theme=first_theme,
            is_follow_up=False,
        )

    # ------------------------------------------------------------ read state

    async def get(self, user_id: str, topic_id: str, session_id: str) -> InterviewStateResponse:
        _, session = await self._require_session(user_id, topic_id, session_id)
        now = self.clock()
        if session.status == Status.IN_PROGRESS and now > session.deadline_at:
            await self._finalize(session, CompletionReason.TIME_EXPIRED)

        complete = session.status == Status.COMPLETED
        return InterviewStateResponse(
            is_complete=complete,
            session_id=session.id,
            status=session.status,
            deadline_at=session.deadline_at,
            remaining_seconds=0 if complete else remaining_seconds(session.deadline_at, now),
            current_question=None if complete else InterviewQuestionResponse.from_state(session.current_question),
            theme_progress=ThemeProgressResponse.from_session(session),
            exchanges=InterviewExchangeResponse.from_exchanges(session.exchanges),
            completion_reason=session.completion_reason,
            config=InterviewConfigResponse.from_session(session),
            report=await self._ensure_report(session) if complete else None,
        )

    # ------------------------------------------------------------ answer a question

    async def answer(
        self, user_id: str, topic_id: str, session_id: str, request: AnswerInterviewRequest
    ) -> InterviewAnswerResponse:
        topic, session = await self._require_session(user_id, topic_id, session_id)

        if session.status != Status.IN_PROGRESS:
            raise api_error(ErrorCode.INTERVIEW_ALREADY_COMPLETED)

        if self.clock() > session.deadline_at + ANSWER_GRACE:
            await self._finalize(session, CompletionReason.TIME_EXPIRED)
            return InterviewAnswerResponse(
                evaluation=None,
                next_question=None,
                theme_progress=ThemeProgressResponse.from_session(session),
                exchange=None,
                remaining_seconds=0,
                is_complete=True,
            )

        current = session.current_question
        if current is None:
            raise api_error(ErrorCode.NO_ACTIVE_QUESTION)

        answer = (request.answer or "").strip()
        blank = answer == ""
        must_advance_theme = blank or (session.current_follow_up_count or 0) >= MAX_FOLLOW_UPS_PER_THEME

        ai_response = await self._request_next_turn(session, topic.name, current, answer, must_advance_theme)

        if blank:
            # Scoring a blank answer is deterministic: the AI never grades an empty box. Its next question is
            # still used so the interview stays sharp.
            rating, feedback, advance_theme = Rating.WEAK, BLANK_ANSWER_FEEDBACK, True
            next_state = ai_next_question(ai_response) or fallback_next_question(session, topic.name)
        elif (
            ai_response is None
            or ai_response.evaluation is None
            or ai_response.next is None
            or not has_text(ai_response.next.question)
        ):
            logger.warning("Falling back to a deterministic turn: the AI returned no usable turn",
                           extra={"session_id": session_id})
            rating, feedback, advance_theme = Rating.SATISFACTORY, UNSCORED_FEEDBACK, True
            next_state = fallback_next_question(session, topic.name)
        else:
            rating = parse_rating(ai_response.evaluation.rating)
            feedback = first_text(ai_response.evaluation.feedback, DEFAULT_FEEDBACK)
            advance_theme = ai_response.next.advance_theme or must_advance_theme
            next_state = QuestionState(
                question=ai_response.next.question,
                theme=first_text(ai_response.next.theme, current.theme),
                is_follow_up=ai_response.next.is_follow_up and not advance_theme,
            )

        exchange = Exchange(
            question=current.question,
            theme=current.theme,
            is_follow_up=current.is_follow_up,
            user_answer=answer,
            rating=rating,
            points=points_for_rating(None if blank else rating),
            feedback=feedback,
        )
        session.exchanges = [*(session.exchanges or []), exchange]

        # Relabel the question with the theme the session actually landed on, so the UI never shows a question
        # tagged with a theme the interview has already moved past.
        next_state.theme = apply_theme_transition(session, advance_theme, next_state.theme, topic.name)
        session.current_question = next_state
        await self.sessions.save(session)

        return InterviewAnswerResponse(
            evaluation=InterviewEvaluationResponse(rating=rating, feedback=feedback, points=exchange.points),
            next_question=InterviewQuestionResponse.from_state(next_state),
            theme_progress=ThemeProgressResponse.from_session(session),
            exchange=InterviewExchangeResponse.from_exchange(len(session.exchanges), exchange),
            remaining_seconds=remaining_seconds(session.deadline_at, self.clock()),
            is_complete=False,
        )

    async def _request_next_turn(
        self, session: MockInterviewSession, topic_name: str, current: QuestionState, answer: str, must_advance: bool
    ) -> NextTurnResponse | None:
        try:
            return await self.ai.next_turn(
                NextTurnRequest(
                    topic_name=topic_name,
                    experience_level=session.experience_level,
                    difficulty=session.difficulty,
                    theme_plan=session.theme_plan or [],
                    current_theme_index=session.current_theme_index or 0,
                    current_follow_up_count=session.current_follow_up_count or 0,
                    remaining_seconds=remaining_seconds(session.deadline_at, self.clock()),
                    prior_exchanges=[
                        NextTurnExchange(
                            question=e.question,
                            user_answer=e.user_answer,
                            theme=e.theme,
                            is_follow_up=e.is_follow_up,
                            rating=e.rating,
                        )
                        for e in session.exchanges or []
                    ],
                    last_answer=answer,
                    current_question=NextTurnQuestionContext(
                        question=current.question, theme=current.theme, is_follow_up=current.is_follow_up
                    ),
                    must_advance_theme=must_advance,
                    max_follow_ups=MAX_FOLLOW_UPS_PER_THEME,
                )
            )
        except Exception:
            logger.warning("next-turn call failed", exc_info=True, extra={"session_id": session.id})
            return None

    # ------------------------------------------------------------ finalize / report

    async def end(self, user_id: str, topic_id: str, session_id: str) -> InterviewReportResponse:
        _, session = await self._require_session(user_id, topic_id, session_id)
        if session.status == Status.IN_PROGRESS:
            expired = self.clock() > session.deadline_at
            await self._finalize(session, CompletionReason.TIME_EXPIRED if expired else CompletionReason.USER_ENDED)
        return await self._ensure_report(session)

    async def report(self, user_id: str, topic_id: str, session_id: str) -> InterviewReportResponse:
        _, session = await self._require_session(user_id, topic_id, session_id)
        if session.status != Status.COMPLETED:
            raise api_error(ErrorCode.INTERVIEW_NOT_COMPLETED)
        return await self._ensure_report(session)

    async def list(self, user_id: str, topic_id: str) -> list[InterviewSummaryResponse]:
        """Newest first, so the caller can number attempts by position; sessions without createdAt go last."""
        topic = await self._require_topic(user_id, topic_id)
        found = await self.sessions.find_by_topic_and_user(topic.id, user_id)
        dated = sorted((s for s in found if s.created_at is not None), key=lambda s: s.created_at, reverse=True)
        sessions = dated + [s for s in found if s.created_at is None]

        reports = await self.reports.find_by_session_ids([s.id for s in sessions])  # two queries in all
        summaries = []
        for session in sessions:
            report = reports.get(session.id)
            summaries.append(
                InterviewSummaryResponse(
                    session_id=session.id,
                    status=session.status,
                    completion_reason=session.completion_reason,
                    config=InterviewConfigResponse.from_session(session),
                    score=report.score if report else None,
                    max_score=report.max_score if report else None,
                    passed=report.passed if report else None,
                    answered_count=len(session.exchanges or []),
                    created_at=session.created_at,
                    completed_at=session.completed_at,
                )
            )
        return summaries

    async def _finalize(self, session: MockInterviewSession, reason: CompletionReason) -> None:
        if session.status == Status.COMPLETED:
            return
        session.status = Status.COMPLETED
        session.completion_reason = reason
        session.completed_at = self.clock()
        session.current_question = None
        await self.sessions.save(session)

    async def _ensure_report(self, session: MockInterviewSession) -> InterviewReportResponse:
        """The report for a completed session, generated on first request.

        Generation is the one step that can fail transiently, so it is kept apart from finalization: a failed
        AI call still stores a minimal report built from the exchanges (nothing is lost, and the per-answer
        ratings are complete).
        """
        lock = self._report_locks.get(session.id)
        if lock is None:
            lock = self._report_locks[session.id] = asyncio.Lock()
        async with lock:
            existing = await self.reports.find_by_session_id(session.id)
            if existing is not None:
                return InterviewReportResponse.from_report(existing)

            topic = await self.topics.find_by_id_and_user(session.topic_id, session.user_id)
            topic_name = topic.name if topic else "this topic"

            ai_report: GenerateInterviewReportResponse | None
            try:
                ai_report = await self.ai.generate_interview_report(
                    topic_name,
                    session.experience_level,
                    session.difficulty,
                    [
                        ReportExchange(question=e.question, user_answer=e.user_answer, theme=e.theme, rating=e.rating)
                        for e in session.exchanges or []
                    ],
                )
            except Exception:
                logger.warning("Report generation failed; storing a minimal report", exc_info=True,
                               extra={"session_id": session.id})
                ai_report = None

            score = calculate_score(session.exchanges)
            report = await self.reports.insert(
                MockInterviewReport(
                    mock_interview_session_id=session.id,
                    topic_id=session.topic_id,
                    user_id=session.user_id,
                    score=score,
                    max_score=MAX_SCORE,
                    pass_threshold=PASS_THRESHOLD,
                    passed=score >= PASS_THRESHOLD,
                    strengths=(ai_report.strengths if ai_report else None) or [],
                    weaknesses=(ai_report.weaknesses if ai_report else None) or [],
                    improvement_suggestions=[
                        ImprovementSuggestion(
                            question=s.question, user_answer=s.user_answer, theme=s.theme, better_answer=s.better_answer
                        )
                        for s in (ai_report.improvement_suggestions if ai_report else None) or []
                    ],
                    overall_summary=(
                        ai_report.overall_summary
                        if ai_report and has_text(ai_report.overall_summary)
                        else default_summary(session)
                    ),
                    config=Config(
                        experience_level=session.experience_level,
                        difficulty=session.difficulty,
                        duration_minutes=session.duration_minutes,
                    ),
                    completion_reason=session.completion_reason,
                    exchange_summary=list(session.exchanges or []),
                )
            )
            return InterviewReportResponse.from_report(report)

    # ------------------------------------------------------------ response mapping

    def _start_response(self, session: MockInterviewSession, resumed: bool) -> InterviewStartResponse:
        return InterviewStartResponse(
            session_id=session.id,
            deadline_at=session.deadline_at,
            remaining_seconds=remaining_seconds(session.deadline_at, self.clock()),
            current_question=InterviewQuestionResponse.from_state(session.current_question),
            theme_progress=ThemeProgressResponse.from_session(session),
            status=session.status,
            config=InterviewConfigResponse.from_session(session),
            exchanges=InterviewExchangeResponse.from_exchanges(session.exchanges),
            resumed=resumed,
        )
