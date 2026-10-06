import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pymongo
import pytest
import respx
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from app.config import settings
from app.main import app

TEST_MONGODB_URI = os.environ.get("TEST_MONGODB_URI", "mongodb://root:change_me@localhost:27017/?authSource=admin")
AI_URL = "http://ai.test"
AI_STREAM_URL = f"{AI_URL}/ai/learn/stream"
INTERNAL_KEY = "integration-internal-key"
USER = {"X-User-Id": "user-1"}
OTHER_USER = {"X-User-Id": "user-2"}


@pytest.fixture(scope="session")
def mongo_uri():
    probe = pymongo.MongoClient(TEST_MONGODB_URI, serverSelectionTimeoutMS=2000)
    try:
        probe.admin.command("ping")
    except PyMongoError:
        pytest.skip(
            "MongoDB not reachable. Start one with `docker compose -f docker-compose.python.yml up -d mongodb` "
            "or point TEST_MONGODB_URI at it."
        )
    finally:
        probe.close()
    return TEST_MONGODB_URI


@pytest.fixture(scope="module")
def db_name():
    return f"topics_db_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def raw_db(mongo_uri, db_name):
    """Synchronous handle on the test database, for arranging and inspecting data."""
    client = pymongo.MongoClient(mongo_uri, tz_aware=True)
    yield client[db_name]
    client.drop_database(db_name)
    client.close()


@pytest.fixture(scope="module")
def client(mongo_uri, db_name, raw_db):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "mongodb_uri", mongo_uri)
        mp.setattr(settings, "mongodb_db", db_name)
        mp.setattr(settings, "ai_service_url", AI_URL)
        mp.setattr(settings, "internal_api_key", INTERNAL_KEY)
        with TestClient(app) as test_client:
            yield test_client


AI_GENERATE_URL = f"{AI_URL}/ai/test/generate"
AI_EVALUATE_URL = f"{AI_URL}/ai/test/evaluate"


def make_questions(mcq: int = 4, subjective: int = 2) -> list[dict]:
    """Questions as ai-service returns them: with the reference answers included."""
    questions = [
        {"questionId": f"mcq-{i}", "section": "MCQ", "text": f"MCQ {i}?", "options": ["A", "B", "C", "D"],
         "correctOption": "B", "modelAnswer": None}
        for i in range(mcq)
    ]
    questions += [
        {"questionId": f"sub-{i}", "section": "SUBJECTIVE", "text": f"Explain {i}", "options": None,
         "correctOption": None, "modelAnswer": f"model answer {i}"}
        for i in range(subjective)
    ]
    return questions


class FakeTestAi:
    """Stands in for ai-service's /ai/test/* endpoints."""

    def __init__(self, router: respx.MockRouter) -> None:
        self.questions = make_questions()
        self.correct: set[str] | None = None  # None = every answered question is right
        self.strengths = ["Basics"]
        self.weaknesses = ["Internals"]
        self.generate_response: httpx.Response | None = None  # overrides the scripted answer
        self.evaluate_response: httpx.Response | None = None
        self.generate_error: Exception | None = None
        self.evaluate_error: Exception | None = None
        self.drop: set[str] = set()
        self.generate_route = router.post(AI_GENERATE_URL).mock(side_effect=self._generate)
        self.evaluate_route = router.post(AI_EVALUATE_URL).mock(side_effect=self._evaluate)

    def _generate(self, request: httpx.Request) -> httpx.Response:
        if self.generate_error:
            raise self.generate_error
        return self.generate_response or httpx.Response(200, json={"questions": self.questions})

    def _evaluate(self, request: httpx.Request) -> httpx.Response:
        if self.evaluate_error:
            raise self.evaluate_error
        if self.evaluate_response:
            return self.evaluate_response
        answers = json.loads(request.content)["answers"]
        per_question = [
            {"questionId": a["questionId"], "isCorrect": self.correct is None or a["questionId"] in self.correct,
             "evaluation": f"feedback for {a['questionId']}"}
            for a in answers
            if a["questionId"] not in self.drop
        ]
        return httpx.Response(
            200, json={"perQuestion": per_question, "strengths": self.strengths, "weaknesses": self.weaknesses}
        )

    @property
    def generate_calls(self) -> list[dict]:
        return [json.loads(c.request.content) for c in self.generate_route.calls]

    @property
    def evaluate_calls(self) -> list[dict]:
        return [json.loads(c.request.content) for c in self.evaluate_route.calls]


class FakeAiService:
    """Stands in for ai-service: records requests and streams a scripted answer."""

    def __init__(self, router: respx.MockRouter) -> None:
        self.tests = FakeTestAi(router)
        self.tokens = ["Hello", " world"]
        self.status = 200
        self.error = None  # exception to raise instead of answering
        self.mid_stream_error: str | None = None
        self.route = router.post(AI_STREAM_URL).mock(side_effect=self._respond)

    def _respond(self, request: httpx.Request) -> httpx.Response:
        if self.error:
            raise self.error
        if self.status != 200:
            return httpx.Response(self.status, text="ai exploded")
        frames = [f'data: {json.dumps({"token": t})}\n\n' for t in self.tokens]
        if self.mid_stream_error:
            frames.append(f'data: {json.dumps({"error": self.mid_stream_error})}\n\n')
        else:
            frames.append("data: [DONE]\n\n")
        return httpx.Response(200, content="".join(frames).encode(), headers={"content-type": "text/event-stream"})

    @property
    def calls(self) -> list[dict]:
        return [json.loads(c.request.content) for c in self.route.calls]

    @property
    def requests(self) -> list[httpx.Request]:
        return [c.request for c in self.route.calls]


@pytest.fixture
def ai():
    with respx.mock(assert_all_called=False) as router:
        yield FakeAiService(router)


def create_topic(client, name=None, headers=USER) -> dict:
    resp = client.post("/api/v1/topics", json={"name": name or f"Topic {uuid.uuid4().hex[:8]}"}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def parse_sse(text: str) -> list:
    """SSE body -> payloads; '[DONE]' stays a string."""
    frames = []
    for block in text.split("\n\n"):
        if block:
            assert block.startswith("data: "), block
            data = block[len("data: "):]
            frames.append(data if data == "[DONE]" else json.loads(data))
    return frames


def seed_session(raw_db, topic_oid: str, count: int, user_id="user-1") -> datetime:
    """A chat session with `count` alternating AI/USER messages, one second apart. Returns the first timestamp."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    raw_db.chat_sessions.insert_one(
        {
            "userId": user_id,
            "topicId": topic_oid,
            "messages": [
                {"role": "AI" if i % 2 == 0 else "USER", "content": f"m{i}", "timestamp": base + timedelta(seconds=i)}
                for i in range(count)
            ],
            "createdAt": base,
            "updatedAt": base,
        }
    )
    return base
