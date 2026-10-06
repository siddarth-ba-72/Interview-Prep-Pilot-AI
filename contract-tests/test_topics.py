import time
import uuid

import pytest

from conftest import ORIGIN

TOPIC_KEYS = {"id", "name", "createdAt", "testCount", "avgScore"}


def create(user, name=None):
    return user.post("/api/v1/topics", json={"name": name or f"Contract {uuid.uuid4().hex[:8]}"})


def test_create_topic_shape(user):
    resp = create(user, "Kafka Internals")
    assert resp.status_code == 201
    topic = resp.json()
    assert set(topic) == TOPIC_KEYS
    assert topic["name"] == "Kafka Internals"
    assert topic["testCount"] == 0
    assert topic["avgScore"] is None
    uuid.UUID(topic["id"])  # id is the publicId, a UUID
    user.delete(f"/api/v1/topics/{topic['id']}")


def test_duplicate_name_differing_in_case_conflicts(user):
    name = f"CaseTopic {uuid.uuid4().hex[:6]}"
    first = create(user, name)
    assert first.status_code == 201
    dup = create(user, name.upper())
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "DUPLICATE_TOPIC"
    user.delete(f"/api/v1/topics/{first.json()['id']}")


def test_same_name_allowed_for_different_users(user, other_user):
    name = f"Shared {uuid.uuid4().hex[:6]}"
    a, b = create(user, name), create(other_user, name)
    assert a.status_code == 201 and b.status_code == 201
    user.delete(f"/api/v1/topics/{a.json()['id']}")
    other_user.delete(f"/api/v1/topics/{b.json()['id']}")


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_400(user, name):
    resp = user.post("/api/v1/topics", json={"name": name})
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "Topic name is required"


def test_name_over_100_chars_is_400(user):
    resp = user.post("/api/v1/topics", json={"name": "x" * 101})
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "Topic name must be at most 100 characters"


def test_special_characters_in_name(user):
    for name in (f"C++ {uuid.uuid4().hex[:4]}", f"a.b* {uuid.uuid4().hex[:4]}"):
        resp = create(user, name)
        assert resp.status_code == 201
        assert create(user, name.lower()).status_code == 409
        user.delete(f"/api/v1/topics/{resp.json()['id']}")


def test_list_is_newest_first(user):
    created = []
    for _ in range(3):
        created.append(create(user).json())
        time.sleep(0.01)  # createdAt has millisecond precision
    listed = user.get("/api/v1/topics")
    assert listed.status_code == 200
    ids = [t["id"] for t in listed.json()]
    assert all(set(t) == TOPIC_KEYS for t in listed.json())
    mine = [i for i in ids if i in {c["id"] for c in created}]
    assert mine == [c["id"] for c in reversed(created)]
    for c in created:
        user.delete(f"/api/v1/topics/{c['id']}")


def test_delete_then_delete_again(user):
    topic = create(user).json()
    assert user.delete(f"/api/v1/topics/{topic['id']}").status_code == 204
    again = user.delete(f"/api/v1/topics/{topic['id']}")
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "TOPIC_NOT_FOUND"
    assert topic["id"] not in [t["id"] for t in user.get("/api/v1/topics").json()]


def test_other_user_cannot_see_or_delete(user, other_user):
    topic = create(user).json()
    assert topic["id"] not in [t["id"] for t in other_user.get("/api/v1/topics").json()]
    resp = other_user.delete(f"/api/v1/topics/{topic['id']}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TOPIC_NOT_FOUND"
    assert topic["id"] in [t["id"] for t in user.get("/api/v1/topics").json()]
    user.delete(f"/api/v1/topics/{topic['id']}")


def test_topics_require_auth(http):
    assert http.get("/api/v1/topics").status_code == 401
    assert http.post("/api/v1/topics", json={"name": "x"}).status_code == 401


def test_delete_unknown_id_is_404(user):
    resp = user.delete(f"/api/v1/topics/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TOPIC_NOT_FOUND"


def test_cors_preflight(http):
    resp = http.options(
        "/api/v1/topics",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers["access-control-allow-origin"] == ORIGIN
    assert resp.headers["access-control-allow-credentials"] == "true"


@pytest.mark.python_only  # D1: the gateway no longer routes /api/v1/ai/**
def test_ai_routes_are_not_exposed(user):
    resp = user.get("/api/v1/ai/anything")
    assert resp.status_code == 404
