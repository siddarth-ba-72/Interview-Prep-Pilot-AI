"""In-memory stand-ins for Test Mode: repositories and the AI client (named so pytest does not collect it)."""
from datetime import datetime

from app.clients.ai_schemas import (
    AiQuestion,
    AiQuestionEvaluation,
    EvaluateAnswersResponse,
    GenerateTestResponse,
)
from app.models.test_report import TestReport
from app.models.test_session import Answer, Status, TestSession
from app.models.topic import Topic
from app.timeutil import utc_now
from tests.unit.fakes import FakeTopics, oid


class FakeTopicsWithScores(FakeTopics):
    """Same arithmetic as the Mongo pipeline in TopicsRepository.record_test_score."""

    async def record_test_score(self, topic_id: str, raw_score: int) -> Topic | None:
        topic = self.items.get(topic_id)
        if topic is None:
            return None
        topic.test_count = (topic.test_count or 0) + 1
        topic.avg_score = (
            float(raw_score)
            if topic.avg_score is None
            else (topic.avg_score * (topic.test_count - 1) + raw_score) / topic.test_count
        )
        return topic


class FakeSessions:
    __test__ = False

    def __init__(self) -> None:
        self.items: dict[str, TestSession] = {}
        self.lose_the_completion_race = False
        self.find_by_ids_calls = 0

    async def find_by_id(self, session_id: str) -> TestSession | None:
        return self.items.get(session_id)

    async def find_in_progress(self, topic_id: str, user_id: str) -> TestSession | None:
        return next(
            (s for s in self.items.values()
             if s.topic_id == topic_id and s.user_id == user_id and s.status == Status.IN_PROGRESS),
            None,
        )

    async def count_by_topic_and_user(self, topic_id: str, user_id: str) -> int:
        return sum(1 for s in self.items.values() if s.topic_id == topic_id and s.user_id == user_id)

    async def find_by_ids(self, ids: list[str]) -> dict[str, TestSession]:
        self.find_by_ids_calls += 1
        return {i: self.items[i] for i in ids if i in self.items}

    async def insert(self, session: TestSession) -> TestSession:
        session.id = oid(len(self.items) + 1)
        session.created_at = utc_now()
        self.items[session.id] = session
        return session

    async def complete(self, session_id: str, answers: list[Answer], raw_score: int, completed_at: datetime) -> bool:
        session = self.items[session_id]
        if self.lose_the_completion_race or session.status != Status.IN_PROGRESS:
            return False
        session.answers, session.raw_score = answers, raw_score
        session.status, session.completed_at = Status.COMPLETED, completed_at
        return True


class FakeReports:
    __test__ = False

    def __init__(self) -> None:
        self.items: list[TestReport] = []

    async def find_by_session_id(self, session_id: str) -> TestReport | None:
        return next((r for r in self.items if r.test_session_id == session_id), None)

    async def find_latest_attempt(self, topic_id: str, user_id: str) -> TestReport | None:
        mine = [r for r in self.items if r.topic_id == topic_id and r.user_id == user_id]
        return max(mine, key=lambda r: r.attempt_number or 0, default=None)

    async def find_by_topic_and_user(self, topic_id: str, user_id: str) -> list[TestReport]:
        return [r for r in self.items if r.topic_id == topic_id and r.user_id == user_id]

    async def insert(self, report: TestReport) -> TestReport:
        report.id = oid(len(self.items) + 1)
        report.created_at = utc_now()
        self.items.append(report)
        return report


def question(qid: str, section: str = "MCQ") -> AiQuestion:
    if section == "MCQ":
        return AiQuestion(question_id=qid, section="MCQ", text=f"Q {qid}?", options=["A", "B", "C", "D"],
                          correct_option="B")
    return AiQuestion(question_id=qid, section="SUBJECTIVE", text=f"Explain {qid}", model_answer=f"model {qid}")


DEFAULT_QUESTIONS = [question("m1"), question("m2"), question("m3"), question("s1", "SUBJECTIVE"),
                     question("s2", "SUBJECTIVE")]


class FakeTestAi:
    """Scripted generate_test / evaluate_answers that records what it was sent."""

    def __init__(
        self, questions=None, correct: set[str] | None = None, strengths=("Basics",), weaknesses=("Internals",)
    ):
        self.questions = list(questions if questions is not None else DEFAULT_QUESTIONS)
        self.correct = correct  # None = everything correct
        self.strengths, self.weaknesses = list(strengths), list(weaknesses)
        self.generate_calls: list[dict] = []
        self.evaluate_calls: list[dict] = []
        self.drop: set[str] = set()  # question ids the AI "forgets" to evaluate
        self.no_ids = False  # send evaluations without questionIds (position matching)
        self.override: EvaluateAnswersResponse | None = None

    async def generate_test(self, topic_name, strengths, weaknesses) -> GenerateTestResponse:
        self.generate_calls.append({"topic": topic_name, "strengths": strengths, "weaknesses": weaknesses})
        return GenerateTestResponse(questions=list(self.questions))

    async def evaluate_answers(self, topic_name, answers) -> EvaluateAnswersResponse:
        self.evaluate_calls.append({"topic": topic_name, "answers": answers})
        if self.override is not None:
            return self.override
        per_question = [
            AiQuestionEvaluation(
                question_id=None if self.no_ids else a["questionId"],
                is_correct=self.correct is None or a["questionId"] in self.correct,
                evaluation=f"feedback {a['questionId']}",
            )
            for a in answers
            if a["questionId"] not in self.drop
        ]
        return EvaluateAnswersResponse(
            per_question=per_question, strengths=list(self.strengths), weaknesses=list(self.weaknesses)
        )
