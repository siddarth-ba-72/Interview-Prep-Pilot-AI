from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
import respx

from tests.integration.conftest import PASSWORD, TEST_SECRET, login, new_email, refresh_cookie, register

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
FRONTEND = "http://localhost:3000"


def start(client):
    """Begin the flow and return (state, Cookie header for the callback)."""
    resp = client.get("/oauth2/authorization/google", follow_redirects=False)
    state = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]
    return state, f"oauth_state={state}"


def callback(client, state, cookie, code="auth-code", **extra):
    params = {"code": code, "state": state, **extra}
    return client.get("/login/oauth2/code/google", params=params, headers={"Cookie": cookie}, follow_redirects=False)


def mock_google(sub="g-123", email=None, name="Gina Google"):
    email = email or new_email()
    token = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "google-at"}))
    info = respx.get(USERINFO_URL).mock(
        return_value=httpx.Response(200, json={"sub": sub, "email": email, "name": name})
    )
    return email, token, info


def test_auth_google_redirects_to_the_relative_authorization_path(client):
    resp = client.get("/api/v1/auth/google", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/oauth2/authorization/google"


def test_authorization_redirect_and_state_cookie(client):
    resp = client.get("/oauth2/authorization/google", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    query = parse_qs(urlparse(location).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["test-client-id"]
    assert query["redirect_uri"] == [f"{FRONTEND}/login/oauth2/code/google"]
    assert query["scope"] == ["email profile"]
    assert "scope=email%20profile" in location
    assert len(query["state"][0]) >= 32

    raw = next(c for c in resp.headers.get_list("set-cookie") if c.startswith("oauth_state="))
    assert raw.split(";")[0] == f"oauth_state={query['state'][0]}"
    attrs = {a.strip().lower() for a in raw.split(";")[1:]}
    assert attrs == {"httponly", "secure", "samesite=lax", "path=/login/oauth2", "max-age=600"}


def test_each_authorization_gets_a_fresh_state(client):
    assert start(client)[0] != start(client)[0]


@respx.mock
def test_callback_creates_a_new_google_user_and_redirects_with_the_token(client, raw_db):
    email, token_route, info_route = mock_google(sub="g-new-1", name="Gina Google")
    state, cookie = start(client)

    resp = callback(client, state, cookie)

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith(f"{FRONTEND}/auth/callback#token=")
    claims = jwt.decode(location.split("#token=")[1], TEST_SECRET.encode(), algorithms=["HS256"])
    assert claims["email"] == email

    doc = raw_db.users.find_one({"googleId": "g-new-1"})
    assert doc["authProvider"] == "GOOGLE" and doc["displayName"] == "Gina Google"
    assert "passwordHash" not in doc
    assert str(doc["_id"]) == claims["userId"]

    value, raw = refresh_cookie(resp)
    assert value and "path=/api/v1/auth/refresh" in raw.lower() and "httponly" in raw.lower()
    cleared = next(c for c in resp.headers.get_list("set-cookie") if c.startswith("oauth_state="))
    assert "max-age=0" in cleared.lower()

    sent = token_route.calls.last.request
    form = parse_qs(sent.content.decode())
    assert form["grant_type"] == ["authorization_code"] and form["code"] == ["auth-code"]
    assert form["redirect_uri"] == [f"{FRONTEND}/login/oauth2/code/google"]
    assert form["client_id"] == ["test-client-id"] and form["client_secret"] == ["test-client-secret"]
    assert info_route.calls.last.request.headers["authorization"] == "Bearer google-at"


@respx.mock
def test_callback_falls_back_to_email_when_google_sends_no_name(client, raw_db):
    email, _, _ = mock_google(sub="g-noname", name=None)
    state, cookie = start(client)
    assert callback(client, state, cookie).headers["location"].startswith(f"{FRONTEND}/auth/callback#token=")
    assert raw_db.users.find_one({"googleId": "g-noname"})["displayName"] == email


@respx.mock
def test_callback_links_an_existing_password_account_instead_of_duplicating(client, raw_db):
    email, reg = register(client)
    mock_google(sub="g-link-1", email=email)
    state, cookie = start(client)

    resp = callback(client, state, cookie)

    claims = jwt.decode(resp.headers["location"].split("#token=")[1], TEST_SECRET.encode(), algorithms=["HS256"])
    assert claims["userId"] == reg.json()["id"]
    assert raw_db.users.count_documents({"email": email}) == 1
    doc = raw_db.users.find_one({"email": email})
    assert doc["googleId"] == "g-link-1" and doc["passwordHash"].startswith("$2b$")
    assert login(client, email, PASSWORD).status_code == 200  # the password still works


@respx.mock
def test_returning_google_user_is_found_by_google_id(client, raw_db):
    mock_google(sub="g-again", email=new_email())
    for _ in range(2):
        state, cookie = start(client)
        assert "token=" in callback(client, state, cookie).headers["location"]
    assert raw_db.users.count_documents({"googleId": "g-again"}) == 1


@respx.mock
def test_state_mismatch_is_rejected_without_calling_google(client):
    token_route = respx.post(TOKEN_URL)
    state, _ = start(client)
    resp = callback(client, state, "oauth_state=some-other-value")
    assert resp.status_code == 302 and resp.headers["location"] == f"{FRONTEND}/login?error"
    assert not token_route.called
    assert "max-age=0" in next(c for c in resp.headers.get_list("set-cookie") if c.startswith("oauth_state=")).lower()


@respx.mock
def test_missing_state_cookie_is_rejected(client):
    token_route = respx.post(TOKEN_URL)
    state, _ = start(client)
    resp = client.get("/login/oauth2/code/google", params={"code": "c", "state": state}, follow_redirects=False)
    assert resp.headers["location"] == f"{FRONTEND}/login?error"
    assert not token_route.called


@respx.mock
def test_missing_state_param_is_rejected(client):
    _, cookie = start(client)
    resp = client.get(
        "/login/oauth2/code/google", params={"code": "c"}, headers={"Cookie": cookie}, follow_redirects=False
    )
    assert resp.headers["location"] == f"{FRONTEND}/login?error"


@respx.mock
def test_user_denied_access_is_rejected(client):
    token_route = respx.post(TOKEN_URL)
    state, cookie = start(client)
    resp = client.get(
        "/login/oauth2/code/google",
        params={"error": "access_denied", "state": state},
        headers={"Cookie": cookie},
        follow_redirects=False,
    )
    assert resp.status_code == 302 and resp.headers["location"] == f"{FRONTEND}/login?error"
    assert not token_route.called


@pytest.mark.parametrize("failure", ["token_400", "userinfo_500", "no_email", "network"])
@respx.mock
def test_google_failures_redirect_to_the_login_error_page(client, raw_db, failure):
    if failure == "token_400":
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    else:
        if failure == "network":
            respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("down"))
        else:
            respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "at"}))
            body = {"sub": "g-fail"} if failure == "no_email" else {"sub": "g-fail", "email": "x@example.com"}
            status = 500 if failure == "userinfo_500" else 200
            respx.get(USERINFO_URL).mock(return_value=httpx.Response(status, json=body))
    state, cookie = start(client)
    resp = callback(client, state, cookie)
    assert resp.status_code == 302 and resp.headers["location"] == f"{FRONTEND}/login?error"
    assert refresh_cookie(resp) == (None, None)
    assert raw_db.users.find_one({"googleId": "g-fail"}) is None
