import re
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from bson import ObjectId

from tests.integration.conftest import OTHER_USER, USER, create_topic

TOPIC_KEYS = {"id", "name", "createdAt", "testCount", "avgScore"}


def test_missing_user_header_is_401(client):
    for resp in (client.get("/api/v1/topics"), client.post("/api/v1/topics", json={"name": "x"})):
        assert resp.status_code == 401
        assert resp.json() == {"error": {"code": "USER_UNAUTHORIZED", "message": "Missing required header"}}


def test_header_check_comes_before_body_validation(client):
    assert client.post("/api/v1/topics", json={"name": ""}).status_code == 401


def test_create_returns_the_wire_shape_with_nulls_kept(client):
    resp = client.post("/api/v1/topics", json={"name": "Kafka Internals"}, headers=USER)
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == TOPIC_KEYS
    assert body["name"] == "Kafka Internals" and body["testCount"] == 0 and body["avgScore"] is None
    uuid.UUID(body["id"])
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", body["createdAt"])


def test_stored_document_matches_the_spring_shape(client, raw_db):
    body = create_topic(client, "Shape Check")
    doc = raw_db.topics.find_one({"publicId": body["id"]})
    assert set(doc) == {"_id", "publicId", "userId", "name", "testCount", "createdAt"}
    assert isinstance(doc["_id"], ObjectId) and str(doc["_id"]) != body["id"]
    assert doc["userId"] == "user-1" and doc["testCount"] == 0 and type(doc["testCount"]) is int
    assert "avgScore" not in doc and "_class" not in doc  # null fields are omitted, never written as null
    assert doc["createdAt"].tzinfo is not None


def test_a_spring_written_topic_document_is_readable(client, raw_db):
    raw_db.topics.insert_one(
        {"_class": "com.preppilot.topicservice.model.Topic", "publicId": "legacy-1", "userId": "legacy-user",
         "name": "Legacy", "testCount": 3, "avgScore": 41.5}
    )
    listed = client.get("/api/v1/topics", headers={"X-User-Id": "legacy-user"}).json()
    assert [(t["id"], t["name"], t["testCount"], t["avgScore"]) for t in listed] == [("legacy-1", "Legacy", 3, 41.5)]


def test_duplicate_name_differing_in_case_is_409(client):
    name = f"CaseDup {uuid.uuid4().hex[:6]}"
    create_topic(client, name)
    resp = client.post("/api/v1/topics", json={"name": name.upper()}, headers=USER)
    assert resp.status_code == 409
    assert resp.json() == {"error": {"code": "DUPLICATE_TOPIC", "message": f"Topic already exists: {name.upper()}"}}


def test_same_name_is_allowed_for_another_user(client):
    name = f"Shared {uuid.uuid4().hex[:6]}"
    create_topic(client, name)
    create_topic(client, name, headers=OTHER_USER)


@pytest.mark.parametrize(
    "name", ["C++", "a.b*", "(paren)", "[bracket]", "pipe|pipe", "^caret$", "back\\slash", "what?"]
)
def test_regex_metacharacters_in_names(client, name):
    unique = f"{name} {uuid.uuid4().hex[:6]}"
    create_topic(client, unique)
    assert client.post("/api/v1/topics", json={"name": unique.lower()}, headers=USER).status_code == 409


def test_names_with_regex_characters_do_not_collide_with_plain_ones(client):
    suffix = uuid.uuid4().hex[:6]
    create_topic(client, f"abc{suffix}")
    create_topic(client, f"a.c{suffix}")  # a '.' wildcard would have matched the first


def test_name_is_stored_as_submitted(client, raw_db):
    name = f"  Padded {uuid.uuid4().hex[:6]}  "
    create_topic(client, name)
    assert raw_db.topics.find_one({"name": name}) is not None


@pytest.mark.parametrize("payload", [{"name": ""}, {"name": "   "}, {}, {"name": None}])
def test_blank_name_is_400(client, payload):
    resp = client.post("/api/v1/topics", json=payload, headers=USER)
    assert resp.status_code == 400
    assert resp.json() == {"error": {"code": "USER_INVALID_INPUT", "message": "Topic name is required"}}


def test_overlong_name_is_400_and_100_is_fine(client):
    resp = client.post("/api/v1/topics", json={"name": "x" * 101}, headers=USER)
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "Topic name must be at most 100 characters"
    assert client.post("/api/v1/topics", json={"name": "y" * 100}, headers=USER).status_code == 201


def test_list_is_newest_first_and_per_user(client):
    user = {"X-User-Id": f"lister-{uuid.uuid4().hex[:6]}"}
    created = [create_topic(client, f"order-{i}", headers=user) for i in range(4)]
    create_topic(client, "other users topic", headers=OTHER_USER)
    resp = client.get("/api/v1/topics", headers=user)
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()] == [c["id"] for c in reversed(created)]
    assert all(set(t) == TOPIC_KEYS for t in resp.json())


def test_empty_list(client):
    assert client.get("/api/v1/topics", headers={"X-User-Id": "nobody-yet"}).json() == []


def test_delete_returns_204_then_404(client):
    topic = create_topic(client)
    first = client.delete(f"/api/v1/topics/{topic['id']}", headers=USER)
    assert first.status_code == 204 and first.content == b""
    again = client.delete(f"/api/v1/topics/{topic['id']}", headers=USER)
    assert again.status_code == 404
    assert again.json() == {"error": {"code": "TOPIC_NOT_FOUND", "message": f"Topic not found: {topic['id']}"}}
    assert topic["id"] not in [t["id"] for t in client.get("/api/v1/topics", headers=USER).json()]


def test_another_user_cannot_delete_or_see_a_topic(client):
    topic = create_topic(client)
    assert client.delete(f"/api/v1/topics/{topic['id']}", headers=OTHER_USER).status_code == 404
    assert topic["id"] not in [t["id"] for t in client.get("/api/v1/topics", headers=OTHER_USER).json()]
    assert topic["id"] in [t["id"] for t in client.get("/api/v1/topics", headers=USER).json()]


def test_delete_removes_the_chat_session_but_leaves_tests_and_interviews_orphaned(client, raw_db, ai):
    topic = create_topic(client)
    client.get(f"/api/v1/topics/{topic['id']}/chat", headers=USER)  # creates the session
    topic_oid = str(raw_db.topics.find_one({"publicId": topic["id"]})["_id"])
    assert raw_db.chat_sessions.count_documents({"topicId": topic_oid}) == 1
    raw_db.test_sessions.insert_one({"topicId": topic_oid, "userId": "user-1"})

    assert client.delete(f"/api/v1/topics/{topic['id']}", headers=USER).status_code == 204

    assert raw_db.chat_sessions.count_documents({"topicId": topic_oid}) == 0
    assert raw_db.test_sessions.count_documents({"topicId": topic_oid}) == 1  # known issue K2, deliberately kept


def test_concurrent_creates_of_the_same_name_yield_exactly_one_topic(client):
    name = f"Race {uuid.uuid4().hex[:6]}"
    with ThreadPoolExecutor(8) as pool:
        def create(_):
            return client.post("/api/v1/topics", json={"name": name}, headers=USER).status_code

        codes = list(pool.map(create, range(8)))
    assert codes.count(201) == 1 and codes.count(409) == 7


def test_trailing_slash_is_a_404_not_a_redirect_to_the_internal_host(client):
    resp = client.get("/api/v1/topics/", headers=USER, follow_redirects=False)
    assert resp.status_code == 404


def test_indexes_exist(client, raw_db):
    by_key = {tuple(v["key"]): v for v in raw_db.topics.index_information().values()}
    assert by_key[(("userId", 1), ("name", 1))]["unique"] is True
    assert by_key[(("publicId", 1),)]["unique"] is True and by_key[(("publicId", 1),)]["sparse"] is True
    chat = {tuple(v["key"]): v for v in raw_db.chat_sessions.index_information().values()}
    assert chat[(("userId", 1), ("topicId", 1))]["unique"] is True
    for name in ("test_sessions", "test_reports", "mock_interview_sessions", "mock_interview_reports"):
        keys = {tuple(v["key"]) for v in raw_db[name].index_information().values()}
        assert (("topicId", 1),) in keys and (("userId", 1),) in keys
    assert (("testSessionId", 1),) in {tuple(v["key"]) for v in raw_db.test_reports.index_information().values()}
    reports = raw_db.mock_interview_reports.index_information().values()
    assert (("mockInterviewSessionId", 1),) in {tuple(v["key"]) for v in reports}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
