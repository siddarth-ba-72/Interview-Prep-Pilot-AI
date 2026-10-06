import logging
from dataclasses import dataclass

from app.clients.ai_client import AiClient
from app.clients.ai_schemas import AiQuestionEvaluation, EvaluateAnswersResponse
from app.errors import ErrorCode, api_error, topic_not_found
from app.models.test_report import MAX_SCORE, PASS_THRESHOLD, QuestionResult, TestReport
from app.models.test_session import Answer, Question, Section, Status, TestSession
from app.models.topic import Topic
from app.repositories.test_reports import TestReportsRepository
from app.repositories.test_sessions import TestSessionsRepository
from app.repositories.topics import TopicsRepository
from app.schemas.tests import (
    SubmitTestRequest,
    TestListItemResponse,
    TestReportResponse,
    TestStartResponse,
)
from app.timeutil import utc_now

logger = logging.getLogger(__name__)

MCQ_POINTS = 1
SUBJECTIVE_POINTS = 5
NOT_ANSWERED = "Not answered."


def calculate_points(section: Section, user_answer: str | None, is_correct: bool) -> int:
    """Only None means unanswered (0 points). An empty string is an answer, and will normally be marked wrong."""
    if user_answer is None:
        return 0
    weight = MCQ_POINTS if section == Section.MCQ else SUBJECTIVE_POINTS
    return weight if is_correct else -weight


def correct_answer_of(question: Question) -> str | None:
    return question.correct_option if question.section == Section.MCQ else question.model_answer


@dataclass
class Evaluated:
    is_correct: bool | None
    evaluation: str | None


def match_evaluations(questions: list[Question], ai: EvaluateAnswersResponse) -> list[AiQuestionEvaluation]:
    """One evaluation per question, in question order.

    Looked up by questionId; if the AI sent no usable ids at all, matched by position instead.
    """
    per_question = ai.per_question
    if per_question is None:
        raise api_error(ErrorCode.AI_SERVICE_ERROR, "AI Service returned an invalid response")
    by_id = {e.question_id: e for e in per_question if e.question_id}
    use_position = not by_id and bool(per_question)

    matched: list[AiQuestionEvaluation] = []
    for index, question in enumerate(questions):
        evaluation = by_id.get(question.question_id)
        if evaluation is None and use_position and index < len(per_question):
            evaluation = per_question[index]
        if evaluation is None:
            logger.error("No evaluation found for question", extra={"question_id": question.question_id})
            raise api_error(ErrorCode.AI_SERVICE_ERROR, f"No evaluation found for question: {question.question_id}")
        matched.append(evaluation)
    return matched


class TestService:
    __test__ = False  # not a pytest class

    def __init__(
        self,
        topics: TopicsRepository,
        sessions: TestSessionsRepository,
        reports: TestReportsRepository,
        ai: AiClient,
    ) -> None:
        self.topics = topics
        self.sessions = sessions
        self.reports = reports
        self.ai = ai

    async def _topic(self, user_id: str, topic_id: str) -> Topic:
        topic = await self.topics.find_by_public_id_and_user(topic_id, user_id)
        if topic is None:
            raise topic_not_found(topic_id)
        return topic

    async def _session(self, user_id: str, topic: Topic, test_id: str) -> TestSession:
        session = await self.sessions.find_by_id(test_id)
        if session is None or session.user_id != user_id or session.topic_id != topic.id:
            raise api_error(ErrorCode.TEST_NOT_FOUND)  # a malformed id is simply "not found", never a 500
        return session

    async def start(self, user_id: str, topic_id: str) -> TestStartResponse:
        topic = await self._topic(user_id, topic_id)

        existing = await self.sessions.find_in_progress(topic.id, user_id)
        if existing is not None:  # idempotent while a test is in progress
            return TestStartResponse.from_session(existing)

        attempt_number = await self.sessions.count_by_topic_and_user(topic.id, user_id) + 1
        previous = await self.reports.find_latest_attempt(topic.id, user_id)
        strengths = previous.strengths if previous else None
        weaknesses = previous.weaknesses if previous else None
        based_on_previous = previous is not None and bool(weaknesses)

        generated = await self.ai.generate_test(topic.name, strengths, weaknesses)
        if generated.questions is None:
            raise api_error(ErrorCode.AI_SERVICE_ERROR, "AI Service returned an invalid response")
        try:
            questions = [
                Question(
                    question_id=q.question_id,
                    section=Section(q.section),
                    text=q.text,
                    options=q.options,
                    correct_option=q.correct_option,
                    model_answer=q.model_answer,
                )
                for q in generated.questions
            ]
        except ValueError:  # missing id/text or a section that is neither MCQ nor SUBJECTIVE
            logger.error("AI returned an unusable question", exc_info=True)
            raise api_error(ErrorCode.AI_SERVICE_ERROR, "AI Service returned an invalid response") from None

        session = await self.sessions.insert(
            TestSession(
                topic_id=topic.id,
                user_id=user_id,
                status=Status.IN_PROGRESS,
                questions=questions,
                attempt_number=attempt_number,
                based_on_previous_attempt=based_on_previous,
            )
        )
        return TestStartResponse.from_session(session, based_on_previous)

    async def get(self, user_id: str, topic_id: str, test_id: str) -> TestStartResponse:
        topic = await self._topic(user_id, topic_id)
        return TestStartResponse.from_session(await self._session(user_id, topic, test_id))

    async def submit(self, user_id: str, topic_id: str, test_id: str, request: SubmitTestRequest) -> TestReportResponse:
        topic = await self._topic(user_id, topic_id)
        session = await self._session(user_id, topic, test_id)
        if session.status != Status.IN_PROGRESS:
            raise api_error(ErrorCode.TEST_ALREADY_COMPLETED)

        # questionId -> userAnswer; a missing entry (or an explicit null) means not answered. Last one wins.
        user_answers = {a.question_id: a.user_answer for a in request.answers or [] if a.question_id is not None}
        questions = session.questions

        evaluated = await self.ai.evaluate_answers(
            topic.name,
            [
                {
                    "questionId": q.question_id,
                    "section": q.section,
                    "question": q.text,
                    "correctAnswer": correct_answer_of(q),
                    "userAnswer": user_answers.get(q.question_id),
                }
                for q in questions
            ],
        )
        evaluations = match_evaluations(questions, evaluated)

        answers: list[Answer] = []
        raw_score = 0
        for question, evaluation in zip(questions, evaluations, strict=True):
            user_answer = user_answers.get(question.question_id)
            answered = user_answer is not None
            if answered and evaluation.is_correct is None:
                # Java hit a NullPointerException here (500); the AI gave no verdict for an answered question
                raise api_error(ErrorCode.AI_SERVICE_ERROR, f"No evaluation found for question: {question.question_id}")
            points = calculate_points(question.section, user_answer, bool(evaluation.is_correct))
            raw_score += points
            answers.append(
                Answer(
                    question_id=question.question_id,
                    user_answer=user_answer,
                    is_correct=bool(evaluation.is_correct) if answered else False,
                    evaluation=evaluation.evaluation if answered else NOT_ANSWERED,
                    points_awarded=points,
                )
            )

        # Only one concurrent submit can complete the session; the others would otherwise each add a report
        # and count the test twice.
        if not await self.sessions.complete(session.id, answers, raw_score, utc_now()):
            raise api_error(ErrorCode.TEST_ALREADY_COMPLETED)

        updated_topic = await self.topics.record_test_score(topic.id, raw_score)
        avg_score_at_time = updated_topic.avg_score if updated_topic else float(raw_score)

        by_id = {a.question_id: a for a in answers}
        report = await self.reports.insert(
            TestReport(
                test_session_id=session.id,
                topic_id=topic.id,
                user_id=user_id,
                raw_score=raw_score,
                max_score=MAX_SCORE,
                pass_threshold=PASS_THRESHOLD,
                passed=raw_score >= PASS_THRESHOLD,
                avg_score_at_time=avg_score_at_time,
                strengths=evaluated.strengths,
                weaknesses=evaluated.weaknesses,
                question_summary=[
                    QuestionResult(
                        question_id=q.question_id,
                        section=q.section,
                        question_text=q.text,
                        user_answer=by_id[q.question_id].user_answer,
                        correct_answer=correct_answer_of(q),
                        is_correct=by_id[q.question_id].is_correct,
                        evaluation=by_id[q.question_id].evaluation,
                        points_awarded=by_id[q.question_id].points_awarded,
                    )
                    for q in questions
                ],
                attempt_number=session.attempt_number,
                based_on_previous_attempt=bool(session.based_on_previous_attempt),
            )
        )
        return TestReportResponse.from_report(report)

    async def report(self, user_id: str, topic_id: str, test_id: str) -> TestReportResponse:
        topic = await self._topic(user_id, topic_id)
        session = await self._session(user_id, topic, test_id)
        report = await self.reports.find_by_session_id(session.id)
        if report is None:
            raise api_error(ErrorCode.TEST_REPORT_NOT_FOUND)
        return TestReportResponse.from_report(report)

    async def list(self, user_id: str, topic_id: str) -> list[TestListItemResponse]:
        topic = await self._topic(user_id, topic_id)
        reports = await self.reports.find_by_topic_and_user(topic.id, user_id)
        sessions = await self.sessions.find_by_ids([r.test_session_id for r in reports])  # one query, not N
        return [
            TestListItemResponse(
                session_id=r.test_session_id,
                completed_at=sessions[r.test_session_id].completed_at if r.test_session_id in sessions else None,
                raw_score=r.raw_score,
                attempt_number=r.attempt_number,
            )
            for r in reports
        ]
