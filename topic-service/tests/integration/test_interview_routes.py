import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import httpx
import pytest
from bson import ObjectId

from app.timeutil import utc_now
from tests.integration.conftest import OTHER_USER, USER, create_topic

CONFIG = {"experienceLevel": "SENIOR", "difficulty": "MEDIUM", "durationMinutes": 30}
CONFIG_KEYS = {"experienceLevel", "difficulty", "durationMinutes"}
QUESTION_KEYS = {"question", "theme", "isFollowUp"}
PROGRESS_KEYS = {"currentThemeIndex", "totalThemes"}
EXCHANGE_KEYS = {"index", "question", "theme", "isFollowUp", "userAnswer", "rating", "points", "feedback"}
START_KEYS = {"sessionId", "deadlineAt", "remainingSeconds", "currentQuestion", "themeProgress", "status", "config",
              "exchanges", "resumed"}
STATE_KEYS = {"isComplete", "sessionId", "status", "deadlineAt", "remainingSeconds", "currentQuestion",
              "themeProgress", "exchanges", "completionReason", "config", "report"}
ANSWER_KEYS = {"evaluation", "nextQuestion", "themeProgress", "exchange", "remainingSeconds", "isComplete"}
REPORT_KEYS = {"sessionId", "score", "maxScore", "passThreshold", "passed", "strengths", "weaknesses",
               "improvementSuggestions", "overallSummary", "config", "completionReason", "exchangeSummary", "createdAt"}
SUMMARY_KEYS = {"sessionId", "status", "completionReason", "config", "score", "maxScore", "passed", "answeredCount",
                "createdAt", "completedAt"}


@pytest.fixture
def topic(client):
    return create_topic(client)


def url(topic, suffix=""):
    return f"/api/v1/topics/{topic['id']}/interviews{suffix}"


def start(client, topic, config=CONFIG, headers=USER) -> dict:
    resp = client.post(url(topic), json=config, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def say(client, topic, sid, text, headers=USER):
    return client.post(url(topic, f"/{sid}/answer"), json={"answer": text}, headers=headers)


def session_doc(raw_db, sid) -> dict:
    return raw_db.mock_interview_sessions.find_one({"_id": ObjectId(sid)})


def expire(raw_db, sid, seconds_ago=60):
    raw_db.mock_interview_sessions.update_one(
        {"_id": ObjectId(sid)}, {"$set": {"deadlineAt": utc_now() - timedelta(seconds=seconds_ago)}}
    )


# ---------------------------------------------------------------- start / resume

def test_start_returns_the_wire_shape(client, ai, topic):
    ai.interviews.themes = ["Beans", "Security", "Testing"]
    resp = client.post(url(topic), json=CONFIG, headers=USER)
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == START_KEYS
    assert body["resumed"] is False and body["status"] == "IN_PROGRESS" and body["exchanges"] == []
    assert body["config"] == CONFIG and set(body["config"]) == CONFIG_KEYS
    assert set(body["currentQuestion"]) == QUESTION_KEYS
    assert body["currentQuestion"] == {"question": "Opening question?", "theme": "Beans", "isFollowUp": False}
    assert body["themeProgress"] == {"currentThemeIndex": 1, "totalThemes": 3}
    assert 0 < body["remainingSeconds"] <= 1800
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", body["deadlineAt"])
    assert ObjectId.is_valid(body["sessionId"])


def test_start_sends_the_ai_calls_the_spec_describes(client, ai, topic):
    start(client, topic, {"experienceLevel": "junior ", "difficulty": "hard", "durationMinutes": 45})
    assert ai.interviews.plan_calls == [
        {"topicName": topic["name"], "experienceLevel": "JUNIOR", "difficulty": "HARD", "durationMinutes": 45}
    ]
    opener = ai.interviews.turn_calls[0]
    assert opener["themePlan"] == ["Beans", "Security", "Testing"]
    assert (opener["currentThemeIndex"], opener["currentFollowUpCount"], opener["remainingSeconds"]) == (0, 0, 2700)
    assert (opener["priorExchanges"], opener["lastAnswer"], opener["currentQuestion"]) == ([], None, None)
    assert (opener["mustAdvanceTheme"], opener["maxFollowUps"]) == (False, 4)
    request = ai.interviews.plan_route.calls.last.request
    assert request.headers["x-internal-api-key"] == "integration-internal-key" and request.headers["x-request-id"]


def test_session_document_matches_the_spring_shape(client, raw_db, ai, topic):
    body = start(client, topic)
    doc = session_doc(raw_db, body["sessionId"])
    assert set(doc) == {"_id", "topicId", "userId", "status", "experienceLevel", "difficulty", "durationMinutes",
                        "startedAt", "deadlineAt", "themePlan", "currentThemeIndex", "currentFollowUpCount",
                        "currentQuestion", "exchanges", "createdAt"}
    topic_oid = str(raw_db.topics.find_one({"publicId": topic["id"]})["_id"])
    assert doc["topicId"] == topic_oid and doc["userId"] == "user-1" and doc["status"] == "IN_PROGRESS"
    assert doc["themePlan"] == ["Beans", "Security", "Testing"] and doc["exchanges"] == []
    assert (doc["currentThemeIndex"], doc["currentFollowUpCount"]) == (0, 0)
    assert doc["currentQuestion"] == {"question": "Opening question?", "theme": "Beans", "isFollowUp": False}
    assert doc["deadlineAt"] - doc["startedAt"] == timedelta(minutes=30)
    assert doc["startedAt"].tzinfo is not None and "completionReason" not in doc and "completedAt" not in doc


def test_starting_again_resumes_and_ignores_the_new_config(client, ai, topic):
    first = start(client, topic)
    again = client.post(url(topic), json={"experienceLevel": "JUNIOR", "difficulty": "EASY", "durationMinutes": 60},
                        headers=USER)
    assert again.status_code == 201
    body = again.json()
    assert body["resumed"] is True and body["sessionId"] == first["sessionId"] and body["config"] == CONFIG
    assert len(ai.interviews.plan_calls) == 1  # no second plan, no second opener


def test_starting_with_no_body_resumes_a_running_interview(client, ai, topic):
    first = start(client, topic)
    resp = client.post(url(topic), headers=USER)
    assert resp.status_code == 201 and resp.json()["resumed"] is True
    assert resp.json()["sessionId"] == first["sessionId"]


def test_starting_with_no_body_and_nothing_running_is_a_config_error(client, ai, topic):
    resp = client.post(url(topic), headers=USER)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "INVALID_INTERVIEW_CONFIG"


@pytest.mark.parametrize(
    "config, message",
    [
        ({"experienceLevel": "WIZARD", "difficulty": "EASY", "durationMinutes": 30},
         "experienceLevel must be one of [JUNIOR, INTERMEDIATE, SENIOR, MASTER, ADVANCED]"),
        ({"difficulty": "EASY", "durationMinutes": 30},
         "experienceLevel must be one of [JUNIOR, INTERMEDIATE, SENIOR, MASTER, ADVANCED]"),
        ({"experienceLevel": "SENIOR", "difficulty": "IMPOSSIBLE", "durationMinutes": 30},
         "difficulty must be one of [EASY, MEDIUM, HARD]"),
        ({"experienceLevel": "SENIOR", "difficulty": "EASY", "durationMinutes": 25},
         "durationMinutes must be one of 30, 45, or 60"),
        ({"experienceLevel": "SENIOR", "difficulty": "EASY"}, "durationMinutes must be one of 30, 45, or 60"),
    ],
)
def test_invalid_config_is_400(client, ai, topic, config, message):
    resp = client.post(url(topic), json=config, headers=USER)
    assert resp.status_code == 400
    assert resp.json() == {"error": {"code": "INVALID_INTERVIEW_CONFIG", "message": message}}
    assert ai.interviews.plan_calls == []


@pytest.mark.parametrize("minutes", [30, 45, 60])
def test_all_three_durations_work(client, ai, topic, minutes):
    body = start(client, topic, {**CONFIG, "durationMinutes": minutes})
    assert body["config"]["durationMinutes"] == minutes
    assert minutes * 60 - 5 <= body["remainingSeconds"] <= minutes * 60


def test_ai_planning_failure_uses_the_default_plan(client, ai, topic):
    ai.interviews.plan_error = httpx.ConnectError("refused")
    body = start(client, topic, {**CONFIG, "durationMinutes": 60})
    assert body["themeProgress"] == {"currentThemeIndex": 1, "totalThemes": 8}
    assert body["currentQuestion"]["theme"] == f"{topic['name']} fundamentals"


def test_total_ai_outage_still_starts_with_the_fallback_opener(client, ai, topic):
    ai.interviews.plan_error = httpx.ConnectError("refused")
    ai.interviews.turn_error = httpx.ConnectError("refused")
    body = start(client, topic)
    assert body["currentQuestion"]["question"] == (
        f"To get started, tell me about your experience with {topic['name']} fundamentals "
        "and how you have applied it in practice."
    )
    assert body["themeProgress"]["totalThemes"] == 4


def test_ai_5xx_and_garbage_are_also_survivable(client, ai, topic):
    ai.interviews.plan_response = httpx.Response(500, text="boom")
    ai.interviews.turn_response = httpx.Response(200, text="not json")
    body = start(client, topic)
    assert body["themeProgress"]["totalThemes"] == 4 and body["currentQuestion"]["question"].startswith("To get started")


def test_the_ai_plan_is_deduplicated(client, ai, topic):
    ai.interviews.plan_response = httpx.Response(200, json={"themes": [" Beans ", "beans", "", "Security"]})
    assert start(client, topic)["themeProgress"]["totalThemes"] == 2


def test_start_for_unknown_topic_is_404(client, ai):
    resp = client.post("/api/v1/topics/nope/interviews", json=CONFIG, headers=USER)
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "TOPIC_NOT_FOUND"


def test_an_expired_session_is_finalized_and_a_new_one_starts(client, raw_db, ai, topic):
    old = start(client, topic)
    expire(raw_db, old["sessionId"])
    fresh = start(client, topic, {"experienceLevel": "JUNIOR", "difficulty": "EASY", "durationMinutes": 45})
    assert fresh["resumed"] is False and fresh["sessionId"] != old["sessionId"]
    assert fresh["config"]["experienceLevel"] == "JUNIOR"
    stored = session_doc(raw_db, old["sessionId"])
    assert stored["status"] == "COMPLETED" and stored["completionReason"] == "TIME_EXPIRED"
    assert "currentQuestion" not in stored and stored["completedAt"].tzinfo is not None


# ---------------------------------------------------------------- state

def test_get_state_of_a_running_interview(client, ai, topic):
    started = start(client, topic)
    resp = client.get(url(topic, f"/{started['sessionId']}"), headers=USER)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == STATE_KEYS
    assert body["isComplete"] is False and body["report"] is None and body["completionReason"] is None
    assert body["currentQuestion"] == started["currentQuestion"] and body["config"] == CONFIG
    assert body["deadlineAt"] == started["deadlineAt"] and body["exchanges"] == []


def test_state_survives_a_page_reload_mid_interview(client, ai, topic):
    started = start(client, topic)
    say(client, topic, started["sessionId"], "first answer")
    state = client.get(url(topic, f"/{started['sessionId']}"), headers=USER).json()
    assert [e["userAnswer"] for e in state["exchanges"]] == ["first answer"]
    assert state["currentQuestion"]["question"] == "Question after 1?"
    resumed = client.post(url(topic), json=CONFIG, headers=USER).json()
    assert resumed["resumed"] is True and [e["index"] for e in resumed["exchanges"]] == [1]
    assert resumed["currentQuestion"]["question"] == "Question after 1?"


def test_state_after_the_deadline_finalizes_and_includes_the_report(client, raw_db, ai, topic):
    started = start(client, topic)
    expire(raw_db, started["sessionId"])
    body = client.get(url(topic, f"/{started['sessionId']}"), headers=USER).json()
    assert body["isComplete"] is True and body["status"] == "COMPLETED" and body["completionReason"] == "TIME_EXPIRED"
    assert body["remainingSeconds"] == 0 and body["currentQuestion"] is None
    assert set(body["report"]) == REPORT_KEYS and body["report"]["completionReason"] == "TIME_EXPIRED"


@pytest.mark.parametrize("sid", ["0" * 24, "not-an-object-id", "123"])
def test_unknown_or_malformed_session_ids_are_404(client, ai, topic, sid):
    for resp in (client.get(url(topic, f"/{sid}"), headers=USER), say(client, topic, sid, "x"),
                 client.post(url(topic, f"/{sid}/end"), headers=USER),
                 client.get(url(topic, f"/{sid}/report"), headers=USER)):
        assert resp.status_code == 404
        assert resp.json() == {"error": {"code": "MOCK_INTERVIEW_NOT_FOUND",
                                         "message": f"No mock interview session found with id: {sid}"}}


def test_another_user_or_topic_cannot_reach_a_session(client, ai, topic):
    started = start(client, topic)
    sid = started["sessionId"]
    other_topic = create_topic(client)
    foreign_topic = create_topic(client, headers=OTHER_USER)
    for headers, target in ((USER, other_topic), (OTHER_USER, foreign_topic)):
        assert client.get(url(target, f"/{sid}"), headers=headers).status_code == 404
        assert say(client, target, sid, "x", headers=headers).status_code == 404
        assert client.post(url(target, f"/{sid}/end"), headers=headers).status_code == 404


def test_endpoints_require_the_user_header(client):
    for resp in (client.post("/api/v1/topics/x/interviews", json=CONFIG), client.get("/api/v1/topics/x/interviews"),
                 client.get("/api/v1/topics/x/interviews/y"), client.post("/api/v1/topics/x/interviews/y/end")):
        assert resp.status_code == 401


# ---------------------------------------------------------------- answering

def test_answer_returns_the_wire_shape_and_stores_the_exchange(client, raw_db, ai, topic):
    ai.interviews.rating = "SATISFACTORY"
    started = start(client, topic)
    resp = say(client, topic, started["sessionId"], "  my answer  ")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == ANSWER_KEYS and body["isComplete"] is False
    assert body["evaluation"] == {"rating": "SATISFACTORY", "feedback": "Feedback on: my answer", "points": 60}
    assert set(body["exchange"]) == EXCHANGE_KEYS and body["exchange"]["index"] == 1
    assert body["exchange"] == {"index": 1, "question": "Opening question?", "theme": "Beans", "isFollowUp": False,
                                "userAnswer": "my answer", "rating": "SATISFACTORY", "points": 60,
                                "feedback": "Feedback on: my answer"}
    assert set(body["nextQuestion"]) == QUESTION_KEYS and body["nextQuestion"]["theme"] == "Security"
    assert body["themeProgress"] == {"currentThemeIndex": 2, "totalThemes": 3}

    sent = ai.interviews.turn_calls[1]
    assert sent["lastAnswer"] == "my answer" and sent["mustAdvanceTheme"] is False
    assert sent["currentQuestion"] == {"question": "Opening question?", "theme": "Beans", "isFollowUp": False}

    doc = session_doc(raw_db, started["sessionId"])
    assert doc["exchanges"] == [{"question": "Opening question?", "theme": "Beans", "isFollowUp": False,
                                 "userAnswer": "my answer", "rating": "SATISFACTORY", "points": 60,
                                 "feedback": "Feedback on: my answer"}]
    assert (doc["currentThemeIndex"], doc["currentFollowUpCount"]) == (1, 0)
    assert doc["currentQuestion"]["question"] == "Question after 1?"


def test_follow_ups_keep_the_theme_until_the_budget_is_spent(client, raw_db, ai, topic):
    ai.interviews.advance = False  # the AI keeps drilling the same theme
    started = start(client, topic)
    sid = started["sessionId"]
    for expected_count in (1, 2, 3, 4):
        body = say(client, topic, sid, "answer").json()
        assert body["nextQuestion"]["isFollowUp"] is True and body["themeProgress"]["currentThemeIndex"] == 1
        assert session_doc(raw_db, sid)["currentFollowUpCount"] == expected_count
    fifth = say(client, topic, sid, "answer").json()
    assert ai.interviews.turn_calls[-1]["mustAdvanceTheme"] is True
    assert fifth["themeProgress"]["currentThemeIndex"] == 2 and fifth["nextQuestion"]["isFollowUp"] is False
    assert session_doc(raw_db, sid)["currentFollowUpCount"] == 0


@pytest.mark.parametrize("text", ["", "   "])
def test_blank_answer_scores_zero_whatever_the_ai_says(client, ai, topic, text):
    started = start(client, topic)
    body = say(client, topic, started["sessionId"], text).json()
    assert body["evaluation"] == {"rating": "WEAK", "points": 0,
                                  "feedback": "No answer was submitted for this question, so it scores zero."}
    assert body["exchange"]["userAnswer"] == "" and body["exchange"]["points"] == 0


def test_an_answer_with_no_body_counts_as_blank(client, ai, topic):
    started = start(client, topic)
    resp = client.post(url(topic, f"/{started['sessionId']}/answer"), headers=USER)
    assert resp.status_code == 200 and resp.json()["evaluation"]["points"] == 0


def test_the_plan_grows_when_the_ai_invents_a_theme_past_the_end(client, raw_db, ai, topic):
    ai.interviews.themes = ["Beans"]
    started = start(client, topic)
    ai.interviews.turn_response = httpx.Response(
        200,
        json={"evaluation": {"rating": "STRONG", "feedback": "good"},
              "next": {"question": "Observability?", "theme": "Actuator", "isFollowUp": False, "advanceTheme": True}},
    )
    body = say(client, topic, started["sessionId"], "answer").json()
    assert body["themeProgress"] == {"currentThemeIndex": 2, "totalThemes": 2}
    assert body["nextQuestion"]["theme"] == "Actuator"
    assert session_doc(raw_db, started["sessionId"])["themePlan"] == ["Beans", "Actuator"]


def test_ai_failure_gives_a_fallback_turn_and_the_interview_goes_on(client, raw_db, ai, topic):
    started = start(client, topic)
    ai.interviews.turn_error = httpx.ConnectError("refused")
    body = say(client, topic, started["sessionId"], "answer one").json()
    assert body["isComplete"] is False
    assert body["evaluation"] == {"rating": "SATISFACTORY", "points": 60,
                                  "feedback": "We couldn't score this answer automatically, but it has been recorded."}
    assert "Security" in body["nextQuestion"]["question"] and body["nextQuestion"]["theme"] == "Security"
    second = say(client, topic, started["sessionId"], "answer two").json()
    assert second["nextQuestion"]["question"] != body["nextQuestion"]["question"]  # the templates rotate
    assert len(session_doc(raw_db, started["sessionId"])["exchanges"]) == 2


def test_the_ai_is_retried_once_when_the_connection_fails(client, ai, topic):
    started = start(client, topic)
    calls_before = len(ai.interviews.turn_calls)
    ai.interviews.turn_error = httpx.ConnectError("refused")
    say(client, topic, started["sessionId"], "answer")
    assert ai.interviews.turn_route.call_count - calls_before == 2  # the first try and one retry


def test_answering_a_completed_interview_is_409(client, ai, topic):
    started = start(client, topic)
    client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER)
    resp = say(client, topic, started["sessionId"], "late")
    assert resp.status_code == 409
    assert resp.json() == {"error": {"code": "INTERVIEW_ALREADY_COMPLETED",
                                     "message": "This interview has already been completed."}}


def test_an_answer_just_after_the_deadline_is_still_counted_but_a_late_one_is_not(client, raw_db, ai, topic):
    started = start(client, topic)
    sid = started["sessionId"]
    expire(raw_db, sid, seconds_ago=2)  # inside the 5 s grace period
    assert say(client, topic, sid, "just in time").json()["isComplete"] is False
    expire(raw_db, sid, seconds_ago=10)  # outside it
    late = say(client, topic, sid, "too late").json()
    assert late["isComplete"] is True and late["evaluation"] is None and late["exchange"] is None
    assert late["nextQuestion"] is None and late["remainingSeconds"] == 0
    doc = session_doc(raw_db, sid)
    assert doc["status"] == "COMPLETED" and doc["completionReason"] == "TIME_EXPIRED"
    assert [e["userAnswer"] for e in doc["exchanges"]] == ["just in time"]  # the late one was not recorded


def test_no_active_question_is_409(client, raw_db, ai, topic):
    started = start(client, topic)
    raw_db.mock_interview_sessions.update_one({"_id": ObjectId(started["sessionId"])}, {"$unset": {"currentQuestion": ""}})
    resp = say(client, topic, started["sessionId"], "answer")
    assert resp.status_code == 409
    assert resp.json()["error"] == {"code": "NO_ACTIVE_QUESTION",
                                    "message": "There is no question awaiting an answer on this interview."}


# ---------------------------------------------------------------- end / report

def test_end_returns_the_report_and_closes_the_interview(client, raw_db, ai, topic):
    started = start(client, topic)
    sid = started["sessionId"]
    ai.interviews.rating = "STRONG"
    say(client, topic, sid, "answer one")
    ai.interviews.rating = "WEAK"
    say(client, topic, sid, "answer two")

    resp = client.post(url(topic, f"/{sid}/end"), headers=USER)

    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert set(report) == REPORT_KEYS
    assert (report["sessionId"], report["score"], report["maxScore"], report["passThreshold"]) == (sid, 60, 100, 75)
    assert report["passed"] is False and report["completionReason"] == "USER_ENDED"
    assert report["strengths"] == ["Clear explanations"] and report["weaknesses"] == ["Edge cases"]
    assert report["overallSummary"] == "A decent run."
    assert report["improvementSuggestions"] == [
        {"question": "Q", "userAnswer": "A", "theme": "Beans", "betterAnswer": "A fuller answer"}]
    assert report["config"] == CONFIG
    assert [(e["index"], e["rating"], e["points"]) for e in report["exchangeSummary"]] == [(1, "STRONG", 100), (2, "WEAK", 20)]
    assert all(set(e) == EXCHANGE_KEYS for e in report["exchangeSummary"])
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT.*Z", report["createdAt"])

    sent = ai.interviews.report_calls[0]
    assert (sent["topicName"], sent["experienceLevel"], sent["difficulty"]) == (topic["name"], "SENIOR", "MEDIUM")
    assert [(e["question"], e["userAnswer"], e["theme"], e["rating"]) for e in sent["exchanges"]][0] == (
        "Opening question?", "answer one", "Beans", "STRONG")

    doc = session_doc(raw_db, sid)
    assert doc["status"] == "COMPLETED" and doc["completionReason"] == "USER_ENDED" and "currentQuestion" not in doc


def test_stored_report_document_matches_the_spring_shape(client, raw_db, ai, topic):
    started = start(client, topic)
    say(client, topic, started["sessionId"], "answer")
    client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER)
    doc = raw_db.mock_interview_reports.find_one({"mockInterviewSessionId": started["sessionId"]})
    assert set(doc) == {"_id", "mockInterviewSessionId", "topicId", "userId", "score", "maxScore", "passThreshold",
                        "passed", "strengths", "weaknesses", "improvementSuggestions", "overallSummary", "config",
                        "completionReason", "exchangeSummary", "createdAt"}
    assert doc["topicId"] == str(raw_db.topics.find_one({"publicId": topic["id"]})["_id"])
    assert (doc["score"], doc["maxScore"], doc["passThreshold"], doc["passed"]) == (100, 100, 75, True)
    assert doc["config"] == CONFIG and doc["exchangeSummary"][0]["userAnswer"] == "answer"
    assert doc["createdAt"].tzinfo is not None and type(doc["score"]) is int


def test_report_endpoint_is_409_until_the_interview_is_over(client, ai, topic):
    started = start(client, topic)
    resp = client.get(url(topic, f"/{started['sessionId']}/report"), headers=USER)
    assert resp.status_code == 409
    assert resp.json() == {"error": {"code": "INTERVIEW_NOT_COMPLETED",
                                     "message": "This interview is still in progress - no report has been generated yet."}}


def test_report_endpoint_equals_what_end_returned_and_is_generated_once(client, raw_db, ai, topic):
    started = start(client, topic)
    ended = client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER).json()
    fetched = client.get(url(topic, f"/{started['sessionId']}/report"), headers=USER)
    again = client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER)
    assert fetched.status_code == 200 and fetched.json() == ended and again.json() == ended
    assert len(ai.interviews.report_calls) == 1
    assert raw_db.mock_interview_reports.count_documents({"mockInterviewSessionId": started["sessionId"]}) == 1


def test_ending_with_no_answers_scores_zero_and_fails(client, ai, topic):
    started = start(client, topic)
    report = client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER).json()
    assert (report["score"], report["passed"], report["passThreshold"], report["exchangeSummary"]) == (0, False, 75, [])


def test_end_after_the_deadline_is_time_expired(client, raw_db, ai, topic):
    started = start(client, topic)
    expire(raw_db, started["sessionId"])
    assert client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER).json()["completionReason"] == "TIME_EXPIRED"


@pytest.mark.parametrize("failure", ["error", "500", "garbage", "empty-summary"])
def test_report_survives_ai_failures(client, ai, topic, failure):
    started = start(client, topic)
    say(client, topic, started["sessionId"], "answer")
    if failure == "error":
        ai.interviews.report_error = httpx.ConnectError("refused")
    elif failure == "500":
        ai.interviews.report_response = httpx.Response(500, text="boom")
    elif failure == "garbage":
        ai.interviews.report_response = httpx.Response(200, text="not json")
    else:
        ai.interviews.report_response = httpx.Response(200, json={"strengths": None, "overallSummary": "  "})
    report = client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER)
    assert report.status_code == 200
    body = report.json()
    assert body["score"] == 100 and body["passed"] is True
    assert (body["strengths"], body["weaknesses"], body["improvementSuggestions"]) == ([], [], [])
    assert body["overallSummary"] == (
        "You answered 1 question. A detailed written assessment could not be generated this time, but your "
        "per-question ratings and feedback below are complete."
    )


def test_a_report_for_an_interview_that_never_had_answers_explains_itself(client, ai, topic):
    ai.interviews.report_error = httpx.ConnectError("refused")
    started = start(client, topic)
    report = client.post(url(topic, f"/{started['sessionId']}/end"), headers=USER).json()
    assert report["overallSummary"].startswith("This interview ended before any questions were answered")


def test_concurrent_report_requests_store_exactly_one_report(client, raw_db, ai, topic):
    started = start(client, topic)
    sid = started["sessionId"]
    client.post(url(topic, f"/{sid}/end"), headers=USER)
    raw_db.mock_interview_reports.delete_many({"mockInterviewSessionId": sid})  # as if generation had not run yet
    with ThreadPoolExecutor(6) as pool:
        def fetch(_):
            return client.get(url(topic, f"/{sid}/report"), headers=USER).status_code

        codes = list(pool.map(fetch, range(6)))
    assert set(codes) == {200}
    assert raw_db.mock_interview_reports.count_documents({"mockInterviewSessionId": sid}) == 1


# ---------------------------------------------------------------- list

def test_list_is_newest_first_with_scores_for_finished_ones(client, ai, topic):
    assert client.get(url(topic), headers=USER).json() == []
    first = start(client, topic)
    say(client, topic, first["sessionId"], "answer")
    client.post(url(topic, f"/{first['sessionId']}/end"), headers=USER)
    second = start(client, topic, {"experienceLevel": "JUNIOR", "difficulty": "EASY", "durationMinutes": 45})

    items = client.get(url(topic), headers=USER).json()

    assert [i["sessionId"] for i in items] == [second["sessionId"], first["sessionId"]]
    assert all(set(i) == SUMMARY_KEYS for i in items)
    running, done = items
    assert (running["status"], running["completionReason"], running["score"], running["maxScore"], running["passed"],
            running["answeredCount"], running["completedAt"]) == ("IN_PROGRESS", None, None, None, None, 0, None)
    assert running["config"] == {"experienceLevel": "JUNIOR", "difficulty": "EASY", "durationMinutes": 45}
    assert (done["status"], done["completionReason"], done["score"], done["maxScore"], done["passed"],
            done["answeredCount"]) == ("COMPLETED", "USER_ENDED", 100, 100, True, 1)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT.*Z", done["createdAt"]) and re.fullmatch(r"\d{4}-\d\d-\d\dT.*Z", done["completedAt"])


def test_a_completed_session_with_no_report_yet_is_listed_without_a_score(client, raw_db, ai, topic):
    started = start(client, topic)
    expire(raw_db, started["sessionId"])
    client.post(url(topic), json=CONFIG, headers=USER)  # finalizes the expired one, but never asks for its report
    old = next(i for i in client.get(url(topic), headers=USER).json() if i["sessionId"] == started["sessionId"])
    assert (old["status"], old["completionReason"], old["score"], old["passed"]) == ("COMPLETED", "TIME_EXPIRED", None, None)


def test_list_is_scoped_to_user_and_topic(client, ai, topic):
    start(client, topic)
    assert client.get(url(topic), headers=OTHER_USER).status_code == 404
    assert client.get("/api/v1/topics/nope/interviews", headers=USER).status_code == 404
    assert client.get(url(create_topic(client)), headers=USER).json() == []


def test_spring_written_documents_are_readable(client, raw_db, ai, topic):
    topic_oid = str(raw_db.topics.find_one({"publicId": topic["id"]})["_id"])
    now = utc_now()
    session_id = ObjectId()
    raw_db.mock_interview_sessions.insert_one(
        {"_id": session_id, "_class": "com.preppilot.topicservice.model.MockInterviewSession", "topicId": topic_oid,
         "userId": "user-1", "status": "COMPLETED", "completionReason": "USER_ENDED", "experienceLevel": "SENIOR",
         "difficulty": "HARD", "durationMinutes": 60, "startedAt": now, "deadlineAt": now, "themePlan": ["A", "B"],
         "currentThemeIndex": 1, "currentFollowUpCount": 0, "createdAt": now, "completedAt": now,
         "exchanges": [{"question": "Q", "theme": "A", "isFollowUp": False, "userAnswer": "ans", "rating": "STRONG",
                        "points": 100, "feedback": "ok"}]}
    )
    raw_db.mock_interview_reports.insert_one(
        {"_class": "com.preppilot.topicservice.model.MockInterviewReport", "mockInterviewSessionId": str(session_id),
         "topicId": topic_oid, "userId": "user-1", "score": 88, "maxScore": 100, "passThreshold": 75, "passed": True,
         "strengths": ["a"], "weaknesses": [], "improvementSuggestions": [], "overallSummary": "legacy",
         "config": {"experienceLevel": "SENIOR", "difficulty": "HARD", "durationMinutes": 60},
         "completionReason": "USER_ENDED", "createdAt": now,
         "exchangeSummary": [{"question": "Q", "theme": "A", "isFollowUp": False, "userAnswer": "ans",
                              "rating": "STRONG", "points": 100, "feedback": "ok"}]}
    )
    report = client.get(url(topic, f"/{session_id}/report"), headers=USER).json()
    assert (report["score"], report["overallSummary"], report["config"]["durationMinutes"]) == (88, "legacy", 60)
    state = client.get(url(topic, f"/{session_id}"), headers=USER).json()
    assert state["isComplete"] is True and state["report"]["score"] == 88 and state["themeProgress"] == {
        "currentThemeIndex": 2, "totalThemes": 2}
    listed = client.get(url(topic), headers=USER).json()
    assert listed[0]["score"] == 88 and listed[0]["answeredCount"] == 1
