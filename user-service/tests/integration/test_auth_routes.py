import re
from datetime import timedelta

import pytest

from app.timeutil import utc_now
from tests.integration.conftest import PASSWORD, login, new_email, refresh_cookie, register


def test_register_returns_profile_without_tokens_or_cookie(client):
    email, resp = register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == {"id", "email", "displayName"}
    assert body["email"] == email and body["displayName"] == "Integration User"
    assert refresh_cookie(resp) == (None, None)


def test_stored_user_document_matches_the_spring_shape(client, raw_db):
    email, resp = register(client)
    doc = raw_db.users.find_one({"email": email})
    assert str(doc["_id"]) == resp.json()["id"]
    assert set(doc) == {"_id", "email", "passwordHash", "authProvider", "displayName", "createdAt", "updatedAt"}
    assert doc["authProvider"] == "LOCAL"
    assert doc["passwordHash"].startswith("$2b$12$")
    assert "googleId" not in doc and "_class" not in doc
    assert doc["createdAt"].tzinfo is not None


def test_two_local_users_do_not_collide_on_the_sparse_google_id_index(client):
    assert register(client)[1].status_code == 201
    assert register(client)[1].status_code == 201


def test_duplicate_email_is_409_with_envelope(client):
    email, _ = register(client)
    _, again = register(client, email=email)
    assert again.status_code == 409
    assert again.json() == {"error": {"code": "EMAIL_ALREADY_REGISTERED", "message": "Email already registered"}}


def test_email_is_stored_and_matched_exactly_as_submitted(client, raw_db):
    mixed = f"Mixed.{new_email()}"
    assert register(client, email=mixed)[1].status_code == 201
    assert raw_db.users.find_one({"email": mixed}) is not None
    assert login(client, mixed).status_code == 200
    assert login(client, mixed.lower()).status_code == 401


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"email": "", "password": PASSWORD, "displayName": "A"}, "Email is required"),
        ({"email": "nope", "password": PASSWORD, "displayName": "A"}, "Invalid email format"),
        ({"email": "a@example.com", "password": "", "displayName": "A"}, "Password is required"),
        ({"email": "a@example.com", "password": "short", "displayName": "A"}, "Password must be at least 8 characters"),
        ({"email": "a@example.com", "password": PASSWORD, "displayName": " "}, "Display name is required"),
        ({}, "Email is required"),
    ],
)
def test_register_validation(client, payload, message):
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert resp.json() == {"error": {"code": "USER_INVALID_INPUT", "message": message}}


def test_malformed_json_body_is_400_not_500(client):
    resp = client.post("/api/v1/auth/register", content=b"{not json", headers={"content-type": "application/json"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "USER_INVALID_INPUT"


def test_login_returns_tokens_and_exact_refresh_cookie(client, raw_db):
    email, reg = register(client)
    resp = login(client, email)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"accessToken", "user"}
    assert body["user"] == {"id": reg.json()["id"], "email": email, "displayName": "Integration User"}

    value, raw = refresh_cookie(resp)
    assert re.fullmatch(r"[0-9a-f-]{36}", value)
    attrs = {part.strip().lower() for part in raw.split(";")[1:]}
    assert attrs == {"httponly", "secure", "path=/api/v1/auth/refresh", "max-age=2592000"}  # no Domain, no SameSite

    stored = raw_db.refresh_tokens.find_one({"userId": reg.json()["id"]})
    assert set(stored) == {"_id", "userId", "tokenHash", "expiresAt", "createdAt"}
    assert stored["tokenHash"] != value and len(stored["tokenHash"]) == 64
    assert timedelta(days=29, hours=23) < stored["expiresAt"] - utc_now() <= timedelta(days=30)


def test_login_failures_are_401_with_the_same_envelope(client):
    email, _ = register(client)
    for resp in (login(client, email, "wrong-password"), login(client, new_email())):
        assert resp.status_code == 401
        assert resp.json() == {"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid credentials"}}


def test_login_validation(client):
    assert client.post("/api/v1/auth/login", json={"email": "", "password": "x"}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": ""}).status_code == 400


def test_google_only_account_cannot_password_login(client, raw_db):
    email = new_email()
    raw_db.users.insert_one({"email": email, "authProvider": "GOOGLE", "googleId": "g-x", "displayName": "G"})
    assert login(client, email, PASSWORD).status_code == 401


def test_a_spring_written_bcrypt_hash_can_log_in(client, raw_db):
    import bcrypt

    email = new_email()
    spring_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(12, prefix=b"2a")).decode()
    raw_db.users.insert_one(
        {"_class": "com.preppilot.userservice.model.User", "email": email, "passwordHash": spring_hash,
         "authProvider": "LOCAL", "displayName": "Legacy"}
    )
    resp = login(client, email)
    assert resp.status_code == 200 and resp.json()["user"]["displayName"] == "Legacy"


def test_refresh_rotates_and_consumes_the_old_token(client):
    email, _ = register(client)
    old, _ = refresh_cookie(login(client, email))

    first = client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={old}"})
    assert first.status_code == 200
    assert set(first.json()) == {"accessToken", "user"}
    new, raw = refresh_cookie(first)
    assert new and new != old
    assert "path=/api/v1/auth/refresh" in raw.lower()

    assert client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={old}"}).status_code == 401
    assert client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={new}"}).status_code == 200


def test_refresh_without_cookie_or_with_unknown_token_is_401(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401
    unknown = client.post("/api/v1/auth/refresh", headers={"Cookie": "refresh_token=nope"})
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


def test_expired_refresh_token_is_deleted_and_401(client, raw_db):
    email, reg = register(client)
    value, _ = refresh_cookie(login(client, email))
    expired = {"$set": {"expiresAt": utc_now() - timedelta(minutes=1)}}
    raw_db.refresh_tokens.update_one({"userId": reg.json()["id"]}, expired)
    assert client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={value}"}).status_code == 401
    assert raw_db.refresh_tokens.count_documents({"userId": reg.json()["id"]}) == 0


def test_refresh_token_of_a_deleted_user_is_401(client, raw_db):
    from bson import ObjectId

    email, reg = register(client)
    value, _ = refresh_cookie(login(client, email))
    raw_db.users.delete_one({"_id": ObjectId(reg.json()["id"])})
    assert client.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={value}"}).status_code == 401


def test_logout_clears_the_cookie_and_revokes_a_presented_token(client, raw_db):
    email, reg = register(client)
    value, _ = refresh_cookie(login(client, email))
    resp = client.post("/api/v1/auth/logout", headers={"Cookie": f"refresh_token={value}"})
    assert resp.status_code == 204 and resp.content == b""
    raw = refresh_cookie(resp)[1].lower()
    assert "max-age=0" in raw and "path=/api/v1/auth/refresh" in raw and "httponly" in raw
    assert raw_db.refresh_tokens.count_documents({"userId": reg.json()["id"]}) == 0


def test_logout_without_cookie_is_still_204(client):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    assert "max-age=0" in refresh_cookie(resp)[1].lower()


def test_trailing_slash_is_404_not_a_redirect(client):
    resp = client.post("/api/v1/auth/login/", json={}, follow_redirects=False)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_expected_indexes_exist_with_the_right_options(client, raw_db):
    users = raw_db.users.index_information()
    by_key = {tuple(v["key"]): v for v in users.values()}
    assert by_key[(("email", 1),)]["unique"] is True
    assert by_key[(("googleId", 1),)]["unique"] is True and by_key[(("googleId", 1),)]["sparse"] is True

    tokens = {tuple(v["key"]): v for v in raw_db.refresh_tokens.index_information().values()}
    assert tokens[(("expiresAt", 1),)]["expireAfterSeconds"] == 0
    assert tokens[(("tokenHash", 1),)]["unique"] is True
    assert (("userId", 1),) in tokens


def test_ensuring_indexes_twice_is_a_no_op(client, db_name, raw_db):
    import asyncio

    from app.db import create_client
    from app.main import ensure_indexes

    async def run_again():
        extra = create_client()
        try:
            await ensure_indexes(extra[db_name])
        finally:
            await extra.close()

    asyncio.run(run_again())
    assert len(raw_db.users.index_information()) == 3  # _id, email, googleId
    assert len(raw_db.refresh_tokens.index_information()) == 4  # _id, userId, expiresAt, tokenHash


def test_health_pings_mongo(client):
    assert client.get("/health").json() == {"status": "ok"}
