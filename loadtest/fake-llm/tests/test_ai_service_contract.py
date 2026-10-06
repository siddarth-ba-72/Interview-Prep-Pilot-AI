"""ai-service's real endpoints, run in-process against the fake instead of OpenAI.

If ai-service changes its prompts or its parsing and the fake no longer satisfies it, this is
where it shows up - before a load test fails with a wall of 500s.
"""

import asyncio
import json

import httpx
import pytest
from openai import AsyncOpenAI

import app.llm as ai_llm
from app.config import settings as ai_settings
from app.main import app as ai_app

from fake_llm import main as fake

INTERNAL_KEY = "contract-test-key"


@pytest.fixture(autouse=True)
def ai_service_uses_the_fake(monkeypatch):
    monkeypatch.setattr(ai_settings, "internal_api_key", INTERNAL_KEY)
    monkeypatch.setattr(ai_llm, "_supports_json_mode", True)
    monkeypatch.setattr(ai_llm, "_supports_temperature", True)
    # The client is created per test so it binds to that test's event loop.
    monkeypatch.setattr(ai_llm, "_client", None)


def call(method: str, path: str, body: dict) -> httpx.Response:
    async def run():
        ai_llm._client = AsyncOpenAI(
            api_key="sk-fake",
            base_url="http://fake-llm/v1",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.ASGITransport(app=fake.app), base_url="http://fake-llm"),
        )
        transport = httpx.ASGITransport(app=ai_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://ai-service", timeout=30) as client:
            return await client.request(method, path, json=body, headers={"X-Internal-Api-Key": INTERNAL_KEY})

    return asyncio.run(run())


def test_learn_stream():
    response = call("POST", "/ai/learn/stream", {"topicName": "React", "mode": "CLARIFY", "messages": []})
    events = [line[len("data: "):] for line in response.text.splitlines() if line.startswith("data: ")]

    assert response.status_code == 200
    assert events[-1] == "[DONE]"
    text = "".join(json.loads(e)["token"] for e in events[:-1])
    assert "React" in text
    assert fake.stats.snapshot()["by_scenario"] == {"learn_clarify": 1}


def test_learn_stream_survives_a_dropped_stream():
    fake.settings = fake.settings.updated({"stream_drop_rate": 1})
    response = call("POST", "/ai/learn/stream", {"topicName": "React", "mode": "CLARIFY", "messages": []})
    events = [line[len("data: "):] for line in response.text.splitlines() if line.startswith("data: ")]

    # ai-service turns the broken stream into an error event, which topic-service refunds.
    assert "error" in json.loads(events[-1])


def test_test_generation_and_evaluation():
    generated = call("POST", "/ai/test/generate", {"topicName": "Node.js"})
    assert generated.status_code == 200, generated.text
    questions = generated.json()["questions"]
    assert len(questions) == 20

    answers = [
        {
            "questionId": q["questionId"],
            "section": q["section"],
            "question": q["text"],
            "correctAnswer": q["correctOption"] if q["section"] == "MCQ" else q["modelAnswer"],
            "userAnswer": q["correctOption"] if q["section"] == "MCQ" else "I am not sure.",
        }
        for q in questions
    ]
    evaluated = call("POST", "/ai/test/evaluate", {"topicName": "Node.js", "answers": answers})
    assert evaluated.status_code == 200, evaluated.text
    result = evaluated.json()
    assert {item["questionId"] for item in result["perQuestion"]} == {q["questionId"] for q in questions}
    assert sum(item["isCorrect"] for item in result["perQuestion"]) == 10
    assert fake.stats.snapshot()["by_scenario"] == {"scope_check": 2, "test_generate": 1, "test_evaluate": 1}


def test_test_generation_rejects_off_topic_topics():
    response = call("POST", "/ai/test/generate", {"topicName": "Pasta recipes"})
    assert response.status_code == 400


def test_interview_plan_turns_and_report():
    plan = call("POST", "/ai/interview/plan", {
        "topicName": "Kubernetes", "experienceLevel": "SENIOR", "difficulty": "HARD", "durationMinutes": 30,
    })
    assert plan.status_code == 200, plan.text
    themes = plan.json()["themes"]
    assert len(themes) == 4

    base = {"topicName": "Kubernetes", "experienceLevel": "SENIOR", "difficulty": "HARD", "themePlan": themes}
    opening = call("POST", "/ai/interview/next-turn", base)
    assert opening.status_code == 200, opening.text
    first = opening.json()["next"]
    assert opening.json()["evaluation"] is None

    answer = "Pods are the smallest deployable unit; a Deployment manages ReplicaSets that keep the desired number " * 3
    second = call("POST", "/ai/interview/next-turn", {
        **base,
        "lastAnswer": answer,
        "currentQuestion": {"question": first["question"], "theme": first["theme"], "isFollowUp": False},
    })
    assert second.status_code == 200, second.text
    assert second.json()["evaluation"]["rating"] == "STRONG"
    assert second.json()["next"]["question"] != first["question"]

    report = call("POST", "/ai/interview/generate-report", {
        "topicName": "Kubernetes", "experienceLevel": "SENIOR", "difficulty": "HARD",
        "exchanges": [
            {"question": first["question"], "userAnswer": answer, "theme": first["theme"], "rating": "STRONG"},
            {"question": "How do you debug a CrashLoopBackOff?", "userAnswer": "restart it",
             "theme": themes[1], "rating": "WEAK"},
        ],
    })
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["strengths"] == [first["theme"]]
    assert body["weaknesses"] == [themes[1]]
    assert len(body["improvementSuggestions"]) == 1
    assert body["overallSummary"]


def test_interview_turn_recovers_from_malformed_json(monkeypatch):
    # The first reply is cut off; call_llm_json feeds it back for repair and the second one parses.
    replies = []

    def truncate_first(text):
        replies.append(text)
        return text[: len(text) // 2] if len(replies) == 1 else text

    monkeypatch.setattr(fake, "_make_bad_json", truncate_first)
    fake.settings = fake.settings.updated({"bad_json_rate": 1})
    response = call("POST", "/ai/interview/next-turn", {
        "topicName": "Kubernetes", "experienceLevel": "JUNIOR", "difficulty": "EASY", "themePlan": ["Pods"],
    })
    assert response.status_code == 200, response.text
    assert len(replies) == 2
