import re
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from bson import ObjectId

from tests.integration.conftest import OTHER_USER, USER, create_topic, make_questions

START_KEYS = {"sessionId", "questions", "attemptNumber", "basedOnPreviousAttempt"}
QUESTION_KEYS = {"questionId", "section", "text", "options"}
RESULT_KEYS = {
    "questionId", "section", "questionText", "userAnswer", "correctAnswer", "isCorrect", "evaluation", "pointsAwarded",
}
REPORT_KEYS = {
    "testSessionId", "rawScore", "maxScore", "passThreshold", "passed", "avgScoreAtTime", "strengths", "weaknesses",
    "questionSummary", "attemptNumber", "basedOnPreviousAttempt", "createdAt",
}
LIST_KEYS = {"sessionId", "completedAt", "rawScore", "attemptNumber"}


def url(topic, suffix=""):
    return f"/api/v1/topics/{topic['id']}/tests{suffix}"


def topic_doc(raw_db, topic) -> dict:
    return raw_db.topics.find_one({"publicId": topic["id"]})


def start(client, topic, headers=USER) -> dict:
    resp = client.post(url(topic), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def submit(client, topic, session_id, answers: dict, headers=USER):
    body = {"answers": [{"questionId": k, "userAnswer": v} for k, v in answers.items()]}
    return client.post(url(topic, f"/{session_id}/submit"), json=body, headers=headers)


@pytest.fixture
def topic(client):
    return create_topic(client)


# ---------- start / get ----------

def test_start_returns_the_wire_shape_and_never_the_answers(client, ai, topic):
    resp = client.post(url(topic), headers=USER)
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == START_KEYS
    assert (body["attemptNumber"], body["basedOnPreviousAttempt"]) == (1, False)
    assert len(body["questions"]) == 6
    assert all(set(q) == QUESTION_KEYS for q in body["questions"])
    assert body["questions"][0]["options"] == ["A", "B", "C", "D"] and body["questions"][4]["options"] is None
    assert "correctOption" not in resp.text and "modelAnswer" not in resp.text and "model answer" not in resp.text
    assert ai.tests.generate_calls == [{"topicName": topic["name"], "strengths": None, "weaknesses": None}]
    assert ObjectId.is_valid(body["sessionId"])


def test_session_document_matches_the_spring_shape(client, raw_db, ai, topic):
    body = start(client, topic)
    doc = raw_db.test_sessions.find_one({"_id": ObjectId(body["sessionId"])})
    assert set(doc) == {"_id", "topicId", "userId", "status", "questions", "attemptNumber",
                        "basedOnPreviousAttempt", "createdAt"}
    assert doc["topicId"] == str(topic_doc(raw_db, topic)["_id"]) and doc["topicId"] != topic["id"]
    assert doc["status"] == "IN_PROGRESS" and doc["userId"] == "user-1"
    assert set(doc["questions"][0]) == {"questionId", "section", "text", "options", "correctOption"}
    assert set(doc["questions"][4]) == {"questionId", "section", "text", "modelAnswer"}  # nulls are omitted
    assert doc["createdAt"].tzinfo is not None and "answers" not in doc and "rawScore" not in doc


def test_start_is_idempotent_while_in_progress(client, ai, topic):
    first, second = start(client, topic), start(client, topic)
    assert first == second and len(ai.tests.generate_calls) == 1


def test_get_returns_the_same_questions_and_no_answers(client, ai, topic):
    started = start(client, topic)
    resp = client.get(url(topic, f"/{started['sessionId']}"), headers=USER)
    assert resp.status_code == 200 and resp.json() == started


def test_start_for_unknown_topic_is_404(client, ai):
    resp = client.post(f"/api/v1/topics/{uuid.uuid4()}/tests", headers=USER)
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "TOPIC_NOT_FOUND"
    assert ai.tests.generate_calls == []


@pytest.mark.parametrize("test_id", ["0" * 24, "not-an-object-id", "123"])
def test_unknown_or_malformed_test_id_is_404(client, ai, topic, test_id):
    for resp in (
        client.get(url(topic, f"/{test_id}"), headers=USER),
        client.get(url(topic, f"/{test_id}/report"), headers=USER),
        submit(client, topic, test_id, {}),
    ):
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


def test_another_user_or_topic_cannot_reach_a_test(client, ai, topic):
    started = start(client, topic)
    other_topic = create_topic(client)
    foreign_topic = create_topic(client, headers=OTHER_USER)
    for headers, target in ((USER, other_topic), (OTHER_USER, foreign_topic)):
        sid = started["sessionId"]
        assert client.get(url(target, f"/{sid}"), headers=headers).status_code == 404
        assert submit(client, target, sid, {}, headers=headers).status_code == 404
        assert client.get(url(target, f"/{sid}/report"), headers=headers).status_code == 404


# ---------- submit ----------

def test_submit_scores_stores_and_reports(client, raw_db, ai, topic):
    ai.tests.correct = {"mcq-0", "mcq-3", "sub-0"}
    started = start(client, topic)
    answers = {"mcq-0": "B", "mcq-1": "A", "mcq-3": "B", "sub-0": "my essay"}  # mcq-2 and sub-1 unanswered

    resp = submit(client, topic, started["sessionId"], answers)

    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert set(report) == REPORT_KEYS
    assert report["testSessionId"] == started["sessionId"]
    assert (report["rawScore"], report["maxScore"], report["passThreshold"], report["passed"]) == (6, 60, 36, False)
    assert (report["attemptNumber"], report["basedOnPreviousAttempt"]) == (1, False)
    assert (report["strengths"], report["weaknesses"]) == (["Basics"], ["Internals"])
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", report["createdAt"])
    summary = {r["questionId"]: r for r in report["questionSummary"]}
    assert [r["questionId"] for r in report["questionSummary"]] == [q["questionId"] for q in started["questions"]]
    assert all(set(r) == RESULT_KEYS for r in report["questionSummary"])
    assert (summary["mcq-0"]["pointsAwarded"], summary["mcq-0"]["isCorrect"]) == (1, True)
    assert (summary["mcq-1"]["pointsAwarded"], summary["mcq-1"]["isCorrect"]) == (-1, False)
    assert summary["mcq-2"] == {
        "questionId": "mcq-2", "section": "MCQ", "questionText": "MCQ 2?", "userAnswer": None, "correctAnswer": "B",
        "isCorrect": False, "evaluation": "Not answered.", "pointsAwarded": 0,
    }
    assert (summary["sub-0"]["pointsAwarded"], summary["sub-0"]["correctAnswer"]) == (5, "model answer 0")
    assert summary["sub-1"]["evaluation"] == "Not answered."

    sent = ai.tests.evaluate_calls[0]
    assert sent["topicName"] == topic["name"] and len(sent["answers"]) == 6
    by_id = {a["questionId"]: a for a in sent["answers"]}
    assert by_id["mcq-0"] == {"questionId": "mcq-0", "section": "MCQ", "question": "MCQ 0?", "correctAnswer": "B",
                              "userAnswer": "B"}
    assert by_id["sub-1"] == {"questionId": "sub-1", "section": "SUBJECTIVE", "question": "Explain 1",
                              "correctAnswer": "model answer 1", "userAnswer": None}


def test_stored_session_and_report_documents(client, raw_db, ai, topic):
    ai.tests.correct = {"mcq-0"}
    started = start(client, topic)
    submit(client, topic, started["sessionId"], {"mcq-0": "B", "mcq-1": "A"})

    session = raw_db.test_sessions.find_one({"_id": ObjectId(started["sessionId"])})
    assert session["status"] == "COMPLETED" and session["rawScore"] == 0 and type(session["rawScore"]) is int
    assert session["completedAt"].tzinfo is not None
    assert [a["questionId"] for a in session["answers"]] == [q["questionId"] for q in started["questions"]]
    first = session["answers"][0]
    assert first == {"questionId": "mcq-0", "userAnswer": "B", "isCorrect": True,
                     "evaluation": "feedback for mcq-0", "pointsAwarded": 1}
    assert "userAnswer" not in session["answers"][2]  # unanswered: the null is not written

    report = raw_db.test_reports.find_one({"testSessionId": started["sessionId"]})
    assert set(report) == {"_id", "testSessionId", "topicId", "userId", "rawScore", "maxScore", "passThreshold",
                           "passed", "avgScoreAtTime", "strengths", "weaknesses", "questionSummary",
                           "attemptNumber", "basedOnPreviousAttempt", "createdAt"}
    assert report["topicId"] == str(topic_doc(raw_db, topic)["_id"])  # the _id hex, not the publicId
    assert (report["maxScore"], report["passThreshold"]) == (60, 36)
    assert type(report["avgScoreAtTime"]) is float


def test_empty_string_answer_counts_as_answered_and_is_marked_wrong(client, ai, topic):
    ai.tests.correct = set()
    started = start(client, topic)
    report = submit(client, topic, started["sessionId"], {"mcq-0": "", "sub-0": ""}).json()
    summary = {r["questionId"]: r for r in report["questionSummary"]}
    assert (summary["mcq-0"]["pointsAwarded"], summary["sub-0"]["pointsAwarded"]) == (-1, -5)
    assert summary["mcq-0"]["userAnswer"] == "" and summary["mcq-0"]["evaluation"] == "feedback for mcq-0"
    assert report["rawScore"] == -6


def test_all_unanswered_scores_zero(client, ai, topic):
    started = start(client, topic)
    report = submit(client, topic, started["sessionId"], {}).json()
    assert (report["rawScore"], report["passed"]) == (0, False)
    assert all(r["pointsAwarded"] == 0 for r in report["questionSummary"])


def test_perfect_score_passes(client, ai, topic):
    ai.tests.questions = make_questions(mcq=10, subjective=10)
    started = start(client, topic)
    answers = {q["questionId"]: "answer" for q in started["questions"]}
    report = submit(client, topic, started["sessionId"], answers).json()
    assert (report["rawScore"], report["passed"]) == (60, True)


def test_missing_answers_field_is_400(client, ai, topic):
    started = start(client, topic)
    resp = client.post(url(topic, f"/{started['sessionId']}/submit"), json={}, headers=USER)
    assert resp.status_code == 400
    assert resp.json() == {"error": {"code": "USER_INVALID_INPUT", "message": "Answers are required"}}
    assert ai.tests.evaluate_calls == []


def test_submitting_twice_is_409_and_costs_no_second_ai_call(client, raw_db, ai, topic):
    started = start(client, topic)
    assert submit(client, topic, started["sessionId"], {}).status_code == 200
    again = submit(client, topic, started["sessionId"], {})
    assert again.status_code == 409
    assert again.json() == {"error": {"code": "TEST_ALREADY_COMPLETED", "message": "Test is already completed"}}
    assert len(ai.tests.evaluate_calls) == 1
    assert raw_db.test_reports.count_documents({"testSessionId": started["sessionId"]}) == 1


def test_concurrent_submits_complete_exactly_once(client, raw_db, ai, topic):
    started = start(client, topic)
    with ThreadPoolExecutor(6) as pool:
        def attempt(_):
            return submit(client, topic, started["sessionId"], {"mcq-0": "B"}).status_code

        codes = list(pool.map(attempt, range(6)))
    assert codes.count(200) == 1 and codes.count(409) == 5
    assert raw_db.test_reports.count_documents({"testSessionId": started["sessionId"]}) == 1
    assert topic_doc(raw_db, topic)["testCount"] == 1  # the test was counted once


# ---------- the topic aggregate (real aggregation pipeline) ----------

def run_test(client, topic, answers: dict) -> dict:
    started = start(client, topic)
    resp = submit(client, topic, started["sessionId"], answers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_running_average_over_three_tests(client, raw_db, ai, topic):
    ai.tests.questions = make_questions(mcq=0, subjective=4)  # 5 points each
    ai.tests.correct = {"sub-0", "sub-1", "sub-2", "sub-3"}
    first = run_test(client, topic, {"sub-0": "x", "sub-1": "x"})  # +10
    second = run_test(client, topic, {f"sub-{i}": "x" for i in range(4)})  # +20
    ai.tests.correct = set()
    third = run_test(client, topic, {"sub-0": "x"})  # -5

    assert (first["rawScore"], second["rawScore"], third["rawScore"]) == (10, 20, -5)
    assert first["avgScoreAtTime"] == 10.0
    assert second["avgScoreAtTime"] == 15.0
    assert third["avgScoreAtTime"] == pytest.approx(25 / 3)

    doc = topic_doc(raw_db, topic)
    assert doc["testCount"] == 3 and type(doc["testCount"]) is int
    assert doc["avgScore"] == pytest.approx(25 / 3) and type(doc["avgScore"]) is float
    listed = next(t for t in client.get("/api/v1/topics", headers=USER).json() if t["id"] == topic["id"])
    assert listed["testCount"] == 3 and listed["avgScore"] == pytest.approx(25 / 3)


def test_aggregate_starts_from_a_spring_topic_without_score_fields(client, raw_db, ai, topic):
    raw_db.topics.update_one({"publicId": topic["id"]}, {"$unset": {"testCount": "", "avgScore": ""}})
    report = run_test(client, topic, {"mcq-0": "B"})
    assert report["avgScoreAtTime"] == 1.0
    doc = topic_doc(raw_db, topic)
    assert doc["testCount"] == 1 and doc["avgScore"] == 1.0


def test_concurrent_tests_on_different_topics_do_not_interfere_with_each_other(client, raw_db, ai):
    topics = [create_topic(client) for _ in range(4)]
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda t: run_test(client, t, {"mcq-0": "B"}), topics))
    assert [topic_doc(raw_db, t)["testCount"] for t in topics] == [1, 1, 1, 1]


# ---------- second attempts ----------

def test_second_attempt_is_biased_by_the_first_report(client, raw_db, ai, topic):
    first = start(client, topic)
    submit(client, topic, first["sessionId"], {})
    ai.tests.strengths, ai.tests.weaknesses = ["Other"], ["Other weak"]

    second = start(client, topic)

    assert second["sessionId"] != first["sessionId"]
    assert (second["attemptNumber"], second["basedOnPreviousAttempt"]) == (2, True)
    assert ai.tests.generate_calls[1] == {
        "topicName": topic["name"], "strengths": ["Basics"], "weaknesses": ["Internals"],
    }
    report = submit(client, topic, second["sessionId"], {}).json()
    assert (report["attemptNumber"], report["basedOnPreviousAttempt"]) == (2, True)
    assert (report["strengths"], report["weaknesses"]) == (["Other"], ["Other weak"])


# ---------- report and list ----------

def test_report_404_until_submitted_then_equals_the_submit_response(client, ai, topic):
    started = start(client, topic)
    missing = client.get(url(topic, f"/{started['sessionId']}/report"), headers=USER)
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "TEST_REPORT_NOT_FOUND", "message": "Report not found"}}
    submitted = submit(client, topic, started["sessionId"], {"mcq-0": "B"}).json()
    fetched = client.get(url(topic, f"/{started['sessionId']}/report"), headers=USER)
    assert fetched.status_code == 200 and fetched.json() == submitted


def test_list_has_one_item_per_completed_test(client, ai, topic):
    assert client.get(url(topic), headers=USER).json() == []
    ids = []
    for _ in range(3):
        started = start(client, topic)
        submit(client, topic, started["sessionId"], {})
        ids.append(started["sessionId"])
    start(client, topic)  # an in-progress one is not listed
    items = client.get(url(topic), headers=USER).json()
    assert [i["sessionId"] for i in items] == ids and [i["attemptNumber"] for i in items] == [1, 2, 3]
    assert all(set(i) == LIST_KEYS and i["rawScore"] == 0 for i in items)
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT.*Z", i["completedAt"]) for i in items)


def test_list_is_scoped_to_the_user(client, ai, topic):
    started = start(client, topic)
    submit(client, topic, started["sessionId"], {})
    assert client.get(url(topic), headers=OTHER_USER).status_code == 404
    assert client.get("/api/v1/topics/nope/tests", headers=USER).status_code == 404


def test_spring_written_documents_are_readable(client, raw_db, ai, topic):
    topic_oid = str(topic_doc(raw_db, topic)["_id"])
    session_id = ObjectId()
    raw_db.test_sessions.insert_one(
        {"_id": session_id, "_class": "com.preppilot.topicservice.model.TestSession", "topicId": topic_oid,
         "userId": "user-1", "status": "COMPLETED", "questions": [], "attemptNumber": 7, "rawScore": 40,
         "completedAt": raw_db.topics.find_one({"publicId": topic["id"]})["createdAt"]}
    )
    raw_db.test_reports.insert_one(
        {"_class": "com.preppilot.topicservice.model.TestReport", "testSessionId": str(session_id),
         "topicId": topic_oid, "userId": "user-1", "rawScore": 40, "maxScore": 60, "passThreshold": 36,
         "passed": True, "avgScoreAtTime": 40.0, "strengths": ["a"], "weaknesses": [], "attemptNumber": 7,
         "basedOnPreviousAttempt": False, "createdAt": raw_db.topics.find_one({"publicId": topic["id"]})["createdAt"],
         "questionSummary": [{"questionId": "q", "section": "MCQ", "questionText": "Q?", "correctAnswer": "B",
                              "isCorrect": True, "evaluation": "ok", "pointsAwarded": 1}]}
    )
    report = client.get(url(topic, f"/{session_id}/report"), headers=USER).json()
    assert report["rawScore"] == 40 and report["passed"] is True and report["questionSummary"][0]["userAnswer"] is None
    assert client.get(url(topic), headers=USER).json()[0]["attemptNumber"] == 7


# ---------- AI failures ----------

def test_ai_400_on_start_surfaces_the_detail_and_stores_nothing(client, raw_db, ai, topic):
    ai.tests.generate_response = httpx.Response(400, json={"detail": "topic is out of scope"})
    resp = client.post(url(topic), headers=USER)
    assert resp.status_code == 400
    assert resp.json()["error"] == {
        "code": "AI_INVALID_REQUEST",
        "message": "Invalid test request: topic is out of scope",
    }
    assert raw_db.test_sessions.count_documents({"topicId": str(topic_doc(raw_db, topic)["_id"])}) == 0


@pytest.mark.parametrize(
    "configure, status, code, message",
    [
        (lambda t: setattr(t, "generate_response", httpx.Response(500, text="boom")), 502, "AI_SERVICE_ERROR",
         "AI Service error: 500 INTERNAL_SERVER_ERROR"),
        (lambda t: setattr(t, "generate_error", httpx.ConnectError("refused")), 502, "AI_SERVICE_UNAVAILABLE",
         "AI service temporarily unavailable"),
        (lambda t: setattr(t, "generate_error", httpx.ReadTimeout("slow")), 502, "AI_SERVICE_UNAVAILABLE",
         "AI service temporarily unavailable"),
        (lambda t: setattr(t, "generate_response", httpx.Response(200, json={"questions": [{"section": "ESSAY"}]})),
         502, "AI_SERVICE_ERROR", "AI Service returned an invalid response"),
        (lambda t: setattr(t, "generate_response", httpx.Response(200, text="not json")), 502, "AI_SERVICE_ERROR",
         "AI Service returned an invalid response"),
    ],
    ids=["ai-500", "ai-down", "ai-timeout", "bad-section", "not-json"],
)
def test_ai_failures_on_start(client, raw_db, ai, topic, configure, status, code, message):
    configure(ai.tests)
    resp = client.post(url(topic), headers=USER)
    assert resp.status_code == status
    assert resp.json() == {"error": {"code": code, "message": message}}
    assert raw_db.test_sessions.count_documents({"topicId": str(topic_doc(raw_db, topic)["_id"])}) == 0


def test_ai_failure_on_submit_leaves_the_test_open_and_the_score_untouched(client, raw_db, ai, topic):
    started = start(client, topic)
    ai.tests.evaluate_error = httpx.ConnectError("refused")
    resp = submit(client, topic, started["sessionId"], {"mcq-0": "B"})
    assert resp.status_code == 502 and resp.json()["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert raw_db.test_sessions.find_one({"_id": ObjectId(started["sessionId"])})["status"] == "IN_PROGRESS"
    assert raw_db.test_reports.count_documents({"testSessionId": started["sessionId"]}) == 0
    assert topic_doc(raw_db, topic)["testCount"] == 0

    ai.tests.evaluate_error = None  # the user can simply retry
    assert submit(client, topic, started["sessionId"], {"mcq-0": "B"}).status_code == 200


def test_ai_400_on_submit(client, ai, topic):
    started = start(client, topic)
    ai.tests.evaluate_response = httpx.Response(400, text="bad evaluation request")
    resp = submit(client, topic, started["sessionId"], {})
    assert resp.status_code == 400
    assert resp.json()["error"] == {
        "code": "AI_INVALID_REQUEST",
        "message": "Invalid evaluation request: bad evaluation request",
    }


def test_missing_evaluation_for_a_question_is_502_and_nothing_is_saved(client, raw_db, ai, topic):
    started = start(client, topic)
    ai.tests.drop = {"mcq-1"}
    resp = submit(client, topic, started["sessionId"], {"mcq-0": "B"})
    assert resp.status_code == 502
    assert resp.json()["error"] == {"code": "AI_SERVICE_ERROR", "message": "No evaluation found for question: mcq-1"}
    assert raw_db.test_sessions.find_one({"_id": ObjectId(started["sessionId"])})["status"] == "IN_PROGRESS"
    assert topic_doc(raw_db, topic)["testCount"] == 0


def test_evaluations_without_ids_are_matched_by_position(client, ai, topic):
    started = start(client, topic)
    ai.tests.evaluate_response = httpx.Response(
        200,
        json={"perQuestion": [{"isCorrect": True, "evaluation": f"pos {i}"} for i in range(6)],
              "strengths": [], "weaknesses": []},
    )
    report = submit(client, topic, started["sessionId"], {"mcq-0": "B", "sub-1": "x"}).json()
    assert report["rawScore"] == 6
    assert report["questionSummary"][0]["evaluation"] == "pos 0"
    assert report["questionSummary"][5]["evaluation"] == "pos 5"


def test_test_endpoints_require_the_user_header(client):
    for resp in (client.post("/api/v1/topics/x/tests"), client.get("/api/v1/topics/x/tests"),
                 client.get("/api/v1/topics/x/tests/y"), client.get("/api/v1/topics/x/tests/y/report"),
                 client.post("/api/v1/topics/x/tests/y/submit", json={"answers": []})):
        assert resp.status_code == 401
