import pytest

from conftest import (
    AUTH_RESPONSE_KEYS,
    ORIGIN,
    PASSWORD,
    USER_PROFILE_KEYS,
    make_session,
    new_email,
    refresh_cookie_from,
)


def register(http, **overrides):
    body = {"email": new_email(), "password": PASSWORD, "displayName": "Contract User", **overrides}
    return http.post("/api/v1/auth/register", json=body), body


# ---------- register ----------

def test_register_returns_profile_without_tokens(http):
    resp, body = register(http)
    assert resp.status_code == 201
    data = resp.json()
    assert set(data) == USER_PROFILE_KEYS
    assert data["email"] == body["email"]
    assert data["displayName"] == "Contract User"
    assert refresh_cookie_from(resp) == (None, None)


def test_register_duplicate_email_conflicts(http):
    resp, body = register(http)
    assert resp.status_code == 201
    again = http.post("/api/v1/auth/register", json=body)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert again.json()["error"]["message"] == "Email already registered"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"email": ""}, "Email is required"),
        ({"email": "not-an-email"}, "Invalid email format"),
        ({"password": ""}, "Password is required"),
        ({"password": "short"}, "Password must be at least 8 characters"),
        ({"displayName": "   "}, "Display name is required"),
    ],
)
@pytest.mark.python_only  # D4: Spring answered with its default error body, not the {"error": ...} envelope
def test_register_validation_messages(http, overrides, message):
    resp, _ = register(http, **overrides)
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == message


def test_register_validation_is_400(http):
    resp, _ = register(http, password="short")
    assert resp.status_code == 400


# ---------- login ----------

def test_login_returns_tokens_and_refresh_cookie(http):
    resp, body = register(http)
    assert resp.status_code == 201
    login = http.post("/api/v1/auth/login", json={"email": body["email"], "password": PASSWORD})
    assert login.status_code == 200
    data = login.json()
    assert set(data) == AUTH_RESPONSE_KEYS
    assert set(data["user"]) == USER_PROFILE_KEYS
    assert data["accessToken"].count(".") == 2

    value, raw = refresh_cookie_from(login)
    assert value
    attrs = raw.lower()
    assert "httponly" in attrs
    assert "path=/api/v1/auth/refresh" in attrs
    assert "max-age=2592000" in attrs


def test_login_wrong_password_is_401(http):
    _, body = register(http)
    resp = http.post("/api/v1/auth/login", json={"email": body["email"], "password": "wrong-password"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert resp.json()["error"]["message"] == "Invalid credentials"


def test_login_unknown_email_is_401(http):
    resp = http.post("/api/v1/auth/login", json={"email": new_email(), "password": PASSWORD})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_blank_fields_are_400(http):
    assert http.post("/api/v1/auth/login", json={"email": "", "password": PASSWORD}).status_code == 400
    assert http.post("/api/v1/auth/login", json={"email": new_email(), "password": ""}).status_code == 400


# ---------- /users/me ----------

def test_me_with_token(user):
    resp = user.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert set(resp.json()) == USER_PROFILE_KEYS
    assert resp.json()["email"] == user.email
    assert resp.json()["id"] == user.user["id"]


def test_me_without_token_is_401(http):
    assert http.get("/api/v1/users/me").status_code == 401


def test_me_with_tampered_token_is_401(user, http):
    token = user.access_token
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert http.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_me_with_non_bearer_scheme_is_401(user, http):
    assert http.get("/api/v1/users/me", headers={"Authorization": f"Token {user.access_token}"}).status_code == 401


@pytest.mark.python_only  # D4
def test_gateway_401_uses_error_envelope_and_cors_headers(http):
    resp = http.get("/api/v1/users/me", headers={"Origin": ORIGIN})
    assert resp.status_code == 401
    assert resp.json() == {"error": {"code": "USER_UNAUTHORIZED", "message": "Unauthorized"}}
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_spoofed_user_id_header_is_ignored(user, other_user, http):
    resp = http.get(
        "/api/v1/users/me",
        headers={**user.headers, "X-User-Id": other_user.user["id"], "X-User-Email": other_user.email},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == user.user["id"]


# ---------- refresh / logout ----------

def test_refresh_rotates_token(http):
    session = make_session(http)
    first = http.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={session.refresh}"})
    assert first.status_code == 200
    assert set(first.json()) == AUTH_RESPONSE_KEYS
    new_value, raw = refresh_cookie_from(first)
    assert new_value and new_value != session.refresh
    assert "path=/api/v1/auth/refresh" in raw.lower()

    # the presented token was consumed
    reuse = http.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={session.refresh}"})
    assert reuse.status_code == 401
    # the new one works
    again = http.post("/api/v1/auth/refresh", headers={"Cookie": f"refresh_token={new_value}"})
    assert again.status_code == 200


def test_refresh_without_cookie_is_401(http):
    assert http.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_with_unknown_token_is_401(http):
    resp = http.post("/api/v1/auth/refresh", headers={"Cookie": "refresh_token=00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 401


def test_logout_is_204_and_clears_cookie(http):
    session = make_session(http)
    resp = http.post("/api/v1/auth/logout", headers={"Cookie": f"refresh_token={session.refresh}"})
    assert resp.status_code == 204
    _, raw = refresh_cookie_from(resp)
    assert raw and "max-age=0" in raw.lower()


def test_logout_without_cookie_is_204(http):
    assert http.post("/api/v1/auth/logout").status_code == 204


# ---------- Google OAuth entry points ----------

def test_auth_google_redirects_to_oauth_authorization(http):
    resp = http.get("/api/v1/auth/google")
    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/oauth2/authorization/google")


def test_oauth_authorization_redirects_to_google(http):
    resp = http.get("/oauth2/authorization/google")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://accounts.google.com/")
    assert "client_id=" in resp.headers["location"]


@pytest.mark.python_only  # the hand-rolled flow sets this cookie; Spring used its own session
def test_oauth_authorization_sets_state_cookie(http):
    resp = http.get("/oauth2/authorization/google")
    cookies = " ".join(resp.headers.get_list("set-cookie"))
    assert "oauth_state=" in cookies
    assert "state=" in resp.headers["location"]
