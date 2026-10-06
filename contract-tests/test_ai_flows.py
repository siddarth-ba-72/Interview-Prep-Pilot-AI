"""Flows that call the real LLM via ai-service. Run with `-m ai`; skip with `-m "not ai"`."""
import uuid

import pytest

from conftest import parse_frames

pytestmark = pytest.mark.ai

MESSAGE_KEYS = {"role", "content", "timestamp"}
CHAT_KEYS = {"topicId", "messages", "hasMore"}
PAGED_KEYS = {"messages", "hasMore"}

QUESTION_KEYS = {"questionId", "section", "text", "options"}
TEST_START_KEYS = {"sessionId", "questions", "attemptNumber", "basedOnPreviousAttempt"}
QUESTION_RESULT_KEYS = {
    "questionId", "section", "questionText", "userAnswer", "correctAnswer", "isCorrect", "evaluation", "pointsAwarded",
}
TEST_REPORT_KEYS = {
    "testSessionId", "rawScore", "maxScore", "passThreshold", "passed", "avgScoreAtTime", "strengths", "weaknesses",
    "questionSummary", "attemptNumber", "basedOnPreviousAttempt", "createdAt",
}
TEST_LIST_KEYS = {"sessionId", "completedAt", "rawScore", "attemptNumber"}

IV_CONFIG_KEYS = {"experienceLevel", "difficulty", "durationMinutes"}
IV_QUESTION_KEYS = {"question", "theme", "isFollowUp"}
IV_PROGRESS_KEYS = {"currentThemeIndex", "totalThemes"}
IV_EXCHANGE_KEYS = {"index", "question", "theme", "isFollowUp", "userAnswer", "rating", "points", "feedback"}
IV_EVALUATION_KEYS = {"rating", "feedback", "points"}
IV_START_KEYS = {
    "sessionId", "deadlineAt", "remainingSeconds", "currentQuestion", "themeProgress", "status", "config", "exchanges",
    "resumed",
}
IV_ANSWER_KEYS = {"evaluation", "nextQuestion", "themeProgress", "exchange", "remainingSeconds", "isComplete"}
IV_REPORT_KEYS = {
    "sessionId", "score", "maxScore", "passThreshold", "passed", "strengths", "weaknesses", "improvementSuggestions",
    "overallSummary", "config", "completionReason", "exchangeSummary", "createdAt",
}
IV_SUMMARY_KEYS = {
    "sessionId", "status", "completionReason", "config", "score", "maxScore", "passed", "answeredCount", "createdAt",
    "completedAt",
}


# ---------- Learn chat ----------

def test_chat_get_or_create_and_stream(user, topic):
    base = f"/api/v1/topics/{topic['id']}/chat"

    created = user.get(base)
    assert created.status_code == 200
    chat = created.json()
    assert set(chat) == CHAT_KEYS
    assert chat["topicId"] == topic["id"]
    assert chat["hasMore"] is False
    assert len(chat["messages"]) == 1
    assert set(chat["messages"][0]) == MESSAGE_KEYS
    assert chat["messages"][0]["role"] == "AI"
    assert chat["messages"][0]["content"].strip()

    # a second GET returns the same session, not a second clarification
    again = user.get(base).json()
    assert len(again["messages"]) == 1

    frames = parse_frames(user.sse(f"{base}/messages", {"content": "Give me a one-sentence overview."}))
    assert frames[-1] == "[DONE]"
    tokens = [f["token"] for f in frames[:-1]]
    assert tokens and all(isinstance(t, str) for t in tokens)
    assert all(set(f) == {"token"} for f in frames[:-1])

    paged = user.get(f"{base}/messages")
    assert paged.status_code == 200
    assert set(paged.json()) == PAGED_KEYS
    messages = paged.json()["messages"]
    assert [m["role"] for m in messages][-2:] == ["USER", "AI"]
    assert messages[-2]["content"] == "Give me a one-sentence overview."
    assert messages[-1]["content"] == "".join(tokens)


def test_chat_messages_before_cursor(user, topic):
    base = f"/api/v1/topics/{topic['id']}/chat"
    user.get(base)
    first_ts = user.get(f"{base}/messages").json()["messages"][0]["timestamp"]
    older = user.get(f"{base}/messages", params={"before": first_ts})
    assert older.status_code == 200
    assert older.json() == {"messages": [], "hasMore": False}


def test_chat_messages_without_session_is_404(user, topic):
    resp = user.get(f"/api/v1/topics/{topic['id']}/chat/messages")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_chat_unknown_topic(user):
    missing = str(uuid.uuid4())
    assert user.get(f"/api/v1/topics/{missing}/chat").status_code == 404
    frames = parse_frames(user.sse(f"/api/v1/topics/{missing}/chat/messages", {"content": "hello"}))
    assert len(frames) == 1
    assert set(frames[0]) == {"error"} and frames[0]["error"]


def test_chat_blank_message_is_400(user, topic):
    resp = user.post(f"/api/v1/topics/{topic['id']}/chat/messages", json={"content": "  "})
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "Message content is required"


# ---------- Test Mode ----------

def test_test_mode_full_flow(user, topic):
    base = f"/api/v1/topics/{topic['id']}/tests"

    started = user.post(base)
    assert started.status_code == 201
    start = started.json()
    assert set(start) == TEST_START_KEYS
    assert start["attemptNumber"] == 1
    assert start["basedOnPreviousAttempt"] is False
    questions = start["questions"]
    assert len(questions) == 20
    for q in questions:
        assert set(q) == QUESTION_KEYS, "answers must never be sent to the client"
        assert q["section"] in {"MCQ", "SUBJECTIVE"}

    # idempotent while IN_PROGRESS
    assert user.post(base).json()["sessionId"] == start["sessionId"]

    fetched = user.get(f"{base}/{start['sessionId']}")
    assert fetched.status_code == 200
    assert fetched.json()["sessionId"] == start["sessionId"]
    assert [q["questionId"] for q in fetched.json()["questions"]] == [q["questionId"] for q in questions]

    # no report until it is submitted
    assert user.get(f"{base}/{start['sessionId']}/report").status_code == 404

    answers = [{"questionId": q["questionId"], "userAnswer": None} for q in questions]
    submitted = user.post(f"{base}/{start['sessionId']}/submit", json={"answers": answers})
    assert submitted.status_code == 200, submitted.text
    report = submitted.json()
    assert set(report) == TEST_REPORT_KEYS
    assert report["testSessionId"] == start["sessionId"]
    assert report["rawScore"] == 0
    assert report["maxScore"] == 60
    assert report["passThreshold"] == 36
    assert report["passed"] is False
    assert report["attemptNumber"] == 1
    assert len(report["questionSummary"]) == 20
    assert all(set(r) == QUESTION_RESULT_KEYS for r in report["questionSummary"])
    assert all(r["pointsAwarded"] == 0 and r["isCorrect"] is False for r in report["questionSummary"])

    fetched_report = user.get(f"{base}/{start['sessionId']}/report")
    assert fetched_report.status_code == 200
    assert fetched_report.json() == report

    listed = user.get(base)
    assert listed.status_code == 200
    items = listed.json()
    assert [i["sessionId"] for i in items] == [start["sessionId"]]
    assert set(items[0]) == TEST_LIST_KEYS

    topic_row = next(t for t in user.get("/api/v1/topics").json() if t["id"] == topic["id"])
    assert topic_row["testCount"] == 1
    assert topic_row["avgScore"] == 0.0

    # a second attempt after completing is a fresh session built on the previous weaknesses
    second = user.post(base).json()
    assert second["sessionId"] != start["sessionId"]
    assert second["attemptNumber"] == 2


@pytest.mark.python_only  # D3: Java answered these with a generic 500
def test_test_mode_error_codes(user, topic):
    base = f"/api/v1/topics/{topic['id']}/tests"
    missing = "0" * 24
    assert user.get(f"{base}/{missing}").json()["error"]["code"] == "TEST_NOT_FOUND"
    assert user.get(f"{base}/not-an-object-id").status_code == 404

    start = user.post(base).json()
    user.post(f"{base}/{start['sessionId']}/submit", json={"answers": []})
    again = user.post(f"{base}/{start['sessionId']}/submit", json={"answers": []})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "TEST_ALREADY_COMPLETED"


def test_test_mode_unknown_topic(user):
    assert user.post(f"/api/v1/topics/{uuid.uuid4()}/tests").status_code == 404
    assert user.get(f"/api/v1/topics/{uuid.uuid4()}/tests").status_code == 404


# ---------- Mock Interview ----------

def test_mock_interview_full_flow(user, topic):
    base = f"/api/v1/topics/{topic['id']}/interviews"
    config = {"experienceLevel": "SENIOR", "difficulty": "MEDIUM", "durationMinutes": 30}

    started = user.post(base, json=config)
    assert started.status_code == 201, started.text
    start = started.json()
    assert set(start) == IV_START_KEYS
    assert start["resumed"] is False
    assert start["status"] == "IN_PROGRESS"
    assert start["config"] == config
    assert set(start["currentQuestion"]) == IV_QUESTION_KEYS
    assert start["currentQuestion"]["question"].strip()
    assert set(start["themeProgress"]) == IV_PROGRESS_KEYS
    assert start["themeProgress"]["currentThemeIndex"] == 1
    assert start["exchanges"] == []
    assert 0 < start["remainingSeconds"] <= 30 * 60
    sid = start["sessionId"]

    # starting again resumes; the new config is ignored
    resumed = user.post(base, json={"experienceLevel": "JUNIOR", "difficulty": "EASY", "durationMinutes": 60}).json()
    assert resumed["resumed"] is True
    assert resumed["sessionId"] == sid
    assert resumed["config"] == config

    state = user.get(f"{base}/{sid}")
    assert state.status_code == 200
    assert state.json()["isComplete"] is False
    assert state.json()["report"] is None

    answered = user.post(
        f"{base}/{sid}/answer",
        json={"answer": "I would start from the fundamentals, weigh the trade-offs, and validate with load tests."},
    )
    assert answered.status_code == 200, answered.text
    ans = answered.json()
    assert set(ans) == IV_ANSWER_KEYS
    assert ans["isComplete"] is False
    assert set(ans["evaluation"]) == IV_EVALUATION_KEYS
    assert ans["evaluation"]["rating"] in {"STRONG", "SATISFACTORY", "WEAK"}
    assert set(ans["exchange"]) == IV_EXCHANGE_KEYS
    assert ans["exchange"]["index"] == 1
    assert set(ans["nextQuestion"]) == IV_QUESTION_KEYS

    ended = user.post(f"{base}/{sid}/end")
    assert ended.status_code == 200, ended.text
    report = ended.json()
    assert set(report) == IV_REPORT_KEYS
    assert report["sessionId"] == sid
    assert report["maxScore"] == 100
    assert report["passThreshold"] == 75
    assert report["completionReason"] == "USER_ENDED"
    assert report["config"] == config
    assert len(report["exchangeSummary"]) == 1
    assert all(set(e) == IV_EXCHANGE_KEYS for e in report["exchangeSummary"])

    assert user.get(f"{base}/{sid}/report").json() == report

    final = user.get(f"{base}/{sid}").json()
    assert final["isComplete"] is True
    assert final["remainingSeconds"] == 0
    assert final["currentQuestion"] is None
    assert final["report"] == report

    done = user.post(f"{base}/{sid}/answer", json={"answer": "late"})
    assert done.status_code == 409
    assert done.json()["error"]["code"] == "INTERVIEW_ALREADY_COMPLETED"

    listed = user.get(base)
    assert listed.status_code == 200
    assert [i["sessionId"] for i in listed.json()] == [sid]
    row = listed.json()[0]
    assert set(row) == IV_SUMMARY_KEYS
    assert row["status"] == "COMPLETED"
    assert row["answeredCount"] == 1


def test_mock_interview_invalid_config(user, topic):
    base = f"/api/v1/topics/{topic['id']}/interviews"
    for bad in (
        {"experienceLevel": "WIZARD", "difficulty": "MEDIUM", "durationMinutes": 30},
        {"experienceLevel": "SENIOR", "difficulty": "IMPOSSIBLE", "durationMinutes": 30},
        {"experienceLevel": "SENIOR", "difficulty": "MEDIUM", "durationMinutes": 7},
    ):
        resp = user.post(base, json=bad)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_INTERVIEW_CONFIG"


def test_mock_interview_report_before_completion_is_409(user, topic):
    base = f"/api/v1/topics/{topic['id']}/interviews"
    sid = user.post(base, json={"experienceLevel": "JUNIOR", "difficulty": "EASY", "durationMinutes": 30}).json()[
        "sessionId"
    ]
    resp = user.get(f"{base}/{sid}/report")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INTERVIEW_NOT_COMPLETED"
    user.post(f"{base}/{sid}/end")


def test_mock_interview_not_found(user, topic):
    resp = user.get(f"/api/v1/topics/{topic['id']}/interviews/{'0' * 24}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "MOCK_INTERVIEW_NOT_FOUND"
