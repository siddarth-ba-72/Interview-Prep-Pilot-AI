import asyncio
import re
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from bson import ObjectId

from tests.integration.conftest import INTERNAL_KEY, OTHER_USER, USER, create_topic, parse_sse, seed_session

MESSAGE_KEYS = {"role", "content", "timestamp"}


def chat_url(topic, suffix=""):
    return f"/api/v1/topics/{topic['id']}/chat{suffix}"


def topic_oid(raw_db, topic) -> str:
    return str(raw_db.topics.find_one({"publicId": topic["id"]})["_id"])


def stored_messages(raw_db, topic):
    return raw_db.chat_sessions.find_one({"topicId": topic_oid(raw_db, topic)})["messages"]


# ---------- creating the session ----------

def test_first_open_creates_the_session_with_a_clarifying_ai_message(client, raw_db, ai):
    ai.tokens = ["What is your ", "level?"]
    topic = create_topic(client, "Learn Kafka")
    resp = client.get(chat_url(topic), headers=USER)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"topicId", "messages", "hasMore"}
    assert body["topicId"] == topic["id"] and body["hasMore"] is False
    assert [set(m) for m in body["messages"]] == [MESSAGE_KEYS]
    assert (body["messages"][0]["role"], body["messages"][0]["content"]) == ("AI", "What is your level?")
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", body["messages"][0]["timestamp"])

    assert ai.calls == [{"topicName": "Learn Kafka", "mode": "CLARIFY", "messages": []}]
    request = ai.requests[0]
    assert request.headers["x-internal-api-key"] == INTERNAL_KEY
    assert request.headers["accept"] == "text/event-stream"


def test_session_document_matches_the_spring_shape(client, raw_db, ai):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    doc = raw_db.chat_sessions.find_one({"userId": "user-1", "topicId": topic_oid(raw_db, topic)})
    assert set(doc) == {"_id", "userId", "topicId", "messages", "createdAt", "updatedAt"}
    assert doc["topicId"] != topic["id"]  # the topic's _id hex, not its publicId
    assert ObjectId.is_valid(doc["topicId"])
    assert set(doc["messages"][0]) == MESSAGE_KEYS and doc["messages"][0]["timestamp"].tzinfo is not None


def test_second_open_does_not_call_the_ai_again(client, ai):
    topic = create_topic(client)
    first = client.get(chat_url(topic), headers=USER).json()
    second = client.get(chat_url(topic), headers=USER).json()
    assert first == second and len(ai.calls) == 1


def test_open_for_an_unknown_topic_is_404(client, ai):
    resp = client.get(f"/api/v1/topics/{uuid.uuid4()}/chat", headers=USER)
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "TOPIC_NOT_FOUND"
    assert ai.calls == []


def test_another_users_chat_is_not_reachable(client, ai):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    assert client.get(chat_url(topic), headers=OTHER_USER).status_code == 404
    assert client.get(chat_url(topic, "/messages"), headers=OTHER_USER).status_code == 404


@pytest.mark.parametrize(
    "setup, status, code, message",
    [
        (lambda ai: setattr(ai, "status", 500), 502, "AI_SERVICE_ERROR", "AI service error"),
        (lambda ai: setattr(ai, "mid_stream_error", "model overloaded"), 502, "AI_SERVICE_ERROR", "AI service error"),
        (lambda ai: setattr(ai, "error", httpx.ConnectError("refused")), 502, "AI_SERVICE_UNAVAILABLE",
         "AI service temporarily unavailable"),
    ],
    ids=["ai-500", "ai-error-event", "ai-down"],
)
def test_ai_failure_while_creating_the_session(client, raw_db, ai, setup, status, code, message):
    setup(ai)
    topic = create_topic(client)
    resp = client.get(chat_url(topic), headers=USER)
    assert resp.status_code == status
    assert resp.json() == {"error": {"code": code, "message": message}}
    assert raw_db.chat_sessions.count_documents({"topicId": topic_oid(raw_db, topic)}) == 0


# ---------- sending messages ----------

def test_send_message_streams_tokens_then_done_and_persists_both_messages(client, raw_db, ai):
    topic = create_topic(client, "Streaming")
    client.get(chat_url(topic), headers=USER)
    ai.tokens = ["Kafka ", "is a log", "."]

    resp = client.post(chat_url(topic, "/messages"), json={"content": "Explain it"}, headers=USER)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.headers["x-accel-buffering"] == "no"
    assert resp.text == (
        'data: {"token": "Kafka "}\n\n'
        'data: {"token": "is a log"}\n\n'
        'data: {"token": "."}\n\n'
        "data: [DONE]\n\n"
    )
    assert [(m["role"], m["content"]) for m in stored_messages(raw_db, topic)][1:] == [
        ("USER", "Explain it"),
        ("AI", "Kafka is a log."),
    ]


def test_modes_clarify_then_generate_content_then_follow_up(client, ai):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    for text in ("first", "second", "third"):
        client.post(chat_url(topic, "/messages"), json={"content": text}, headers=USER)
    assert [c["mode"] for c in ai.calls] == ["CLARIFY", "GENERATE_CONTENT", "FOLLOW_UP", "FOLLOW_UP"]


def test_ai_gets_the_full_history_including_the_new_message(client, raw_db, ai):
    topic = create_topic(client)
    seed_session(raw_db, topic_oid(raw_db, topic), 25)  # more than one visible page
    client.post(chat_url(topic, "/messages"), json={"content": "newest"}, headers=USER)
    sent = ai.calls[0]["messages"]
    assert len(sent) == 26
    assert sent[0] == {"role": "AI", "content": "m0"} and sent[-1] == {"role": "USER", "content": "newest"}
    assert ai.calls[0]["mode"] == "FOLLOW_UP"


def test_request_id_is_passed_to_the_ai_service_and_echoed(client, ai):
    topic = create_topic(client)
    resp = client.get(chat_url(topic), headers={**USER, "X-Request-Id": "trace-42"})
    assert resp.headers["x-request-id"] == "trace-42"
    assert ai.requests[0].headers["x-request-id"] == "trace-42"


def test_ai_failure_mid_stream_gives_an_error_frame_and_keeps_only_the_user_message(client, raw_db, ai):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    ai.tokens = ["partial"]
    ai.mid_stream_error = "model overloaded"

    resp = client.post(chat_url(topic, "/messages"), json={"content": "question"}, headers=USER)

    assert resp.status_code == 200
    assert parse_sse(resp.text) == [
        {"token": "partial"},
        {"error": "The AI response could not be completed. Please try again."},
    ]
    assert [(m["role"], m["content"]) for m in stored_messages(raw_db, topic)][-1] == ("USER", "question")


@pytest.mark.parametrize(
    "setup", [lambda ai: setattr(ai, "status", 503), lambda ai: setattr(ai, "error", httpx.ConnectError("x"))]
)
def test_ai_down_when_sending_gives_an_error_frame(client, ai, setup):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    setup(ai)
    resp = client.post(chat_url(topic, "/messages"), json={"content": "hi"}, headers=USER)
    assert parse_sse(resp.text) == [{"error": "The AI response could not be completed. Please try again."}]


def test_unknown_topic_is_a_200_stream_with_a_single_error_frame(client, ai):
    missing = str(uuid.uuid4())
    resp = client.post(f"/api/v1/topics/{missing}/chat/messages", json={"content": "hi"}, headers=USER)
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/event-stream")
    assert resp.text == f'data: {{"error": "Topic not found: {missing}"}}\n\n'
    assert ai.calls == []


def test_missing_session_is_a_200_stream_with_a_single_error_frame(client, raw_db, ai):
    topic = create_topic(client)  # never opened, so no session
    resp = client.post(chat_url(topic, "/messages"), json={"content": "hi"}, headers=USER)
    assert resp.status_code == 200
    assert parse_sse(resp.text) == [
        {"error": f"No chat session found for topic: {topic['id']}. Open Learn Mode first."}
    ]
    assert raw_db.chat_sessions.count_documents({"topicId": topic_oid(raw_db, topic)}) == 0


@pytest.mark.parametrize("payload", [{"content": ""}, {"content": "   "}, {}])
def test_blank_message_is_a_plain_400(client, ai, payload):
    topic = create_topic(client)
    resp = client.post(chat_url(topic, "/messages"), json=payload, headers=USER)
    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"error": {"code": "USER_INVALID_INPUT", "message": "Message content is required"}}


def test_missing_header_on_send_is_401(client):
    assert client.post("/api/v1/topics/x/chat/messages", json={"content": "hi"}).status_code == 401


def test_concurrent_messages_are_all_kept(client, raw_db, ai):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    with ThreadPoolExecutor(6) as pool:
        def send(i):
            return client.post(chat_url(topic, "/messages"), json={"content": f"q{i}"}, headers=USER)

        list(pool.map(send, range(6)))
    contents = [m["content"] for m in stored_messages(raw_db, topic)]
    assert sorted(c for c in contents if c.startswith("q")) == [f"q{i}" for i in range(6)]
    assert contents.count("Hello world") == 7  # the clarification plus six answers: no lost updates ($push)


def test_updated_at_moves_when_a_message_is_appended(client, raw_db, ai):
    topic = create_topic(client)
    client.get(chat_url(topic), headers=USER)
    before = raw_db.chat_sessions.find_one({"topicId": topic_oid(raw_db, topic)})["updatedAt"]
    asyncio.run(asyncio.sleep(0.01))
    client.post(chat_url(topic, "/messages"), json={"content": "hi"}, headers=USER)
    after = raw_db.chat_sessions.find_one({"topicId": topic_oid(raw_db, topic)})["updatedAt"]
    assert after > before


# ---------- paging ----------

@pytest.mark.parametrize("count, returned, has_more", [(1, 1, False), (20, 20, False), (21, 20, True), (45, 20, True)])
def test_latest_page_sizes(client, raw_db, ai, count, returned, has_more):
    topic = create_topic(client)
    seed_session(raw_db, topic_oid(raw_db, topic), count)
    opened = client.get(chat_url(topic), headers=USER).json()
    paged = client.get(chat_url(topic, "/messages"), headers=USER).json()
    assert len(opened["messages"]) == returned and opened["hasMore"] is has_more
    assert paged["hasMore"] is has_more and paged["messages"] == opened["messages"]
    assert paged["messages"][-1]["content"] == f"m{count - 1}"
    assert ai.calls == []  # the session already existed


def test_pages_chain_back_through_the_whole_history(client, raw_db, ai):
    topic = create_topic(client)
    seed_session(raw_db, topic_oid(raw_db, topic), 45)
    page = client.get(chat_url(topic, "/messages"), headers=USER).json()
    seen = [m["content"] for m in page["messages"]]
    pages = 1
    while page["hasMore"]:
        before = page["messages"][0]["timestamp"]
        page = client.get(chat_url(topic, "/messages"), params={"before": before}, headers=USER).json()
        seen = [m["content"] for m in page["messages"]] + seen
        pages += 1
    assert pages == 3 and seen == [f"m{i}" for i in range(45)]


def test_before_older_than_everything_is_empty(client, raw_db, ai):
    topic = create_topic(client)
    seed_session(raw_db, topic_oid(raw_db, topic), 5)
    resp = client.get(chat_url(topic, "/messages"), params={"before": "2020-01-01T00:00:00Z"}, headers=USER)
    assert resp.json() == {"messages": [], "hasMore": False}


@pytest.mark.parametrize(
    "before",
    [
        "2026-01-01T00:00:03Z",
        "2026-01-01T00:00:03.000Z",
        "2026-01-01T00:00:03.000000000Z",
        "2026-01-01T00:00:03+00:00",
        "2026-01-01T02:00:03+02:00",
        "2026-01-01T00:00:03",
    ],
)
def test_before_accepts_the_usual_iso_forms(client, raw_db, ai, before):
    topic = create_topic(client)
    seed_session(raw_db, topic_oid(raw_db, topic), 10)
    resp = client.get(chat_url(topic, "/messages"), params={"before": before}, headers=USER)
    assert resp.status_code == 200, resp.text
    assert [m["content"] for m in resp.json()["messages"]] == ["m0", "m1", "m2"]


@pytest.mark.parametrize("before", ["yesterday", "", "2026-13-45", "123"])
def test_malformed_before_is_400_not_500(client, ai, before):
    topic = create_topic(client)
    resp = client.get(chat_url(topic, "/messages"), params={"before": before}, headers=USER)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "USER_INVALID_INPUT"


def test_messages_without_a_session_is_404(client, ai):
    topic = create_topic(client)
    resp = client.get(chat_url(topic, "/messages"), headers=USER)
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {
            "code": "CHAT_SESSION_NOT_FOUND",
            "message": f"No chat session found for topic: {topic['id']}. Open Learn Mode first.",
        }
    }
