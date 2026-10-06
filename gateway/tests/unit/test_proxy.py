import httpx
import pytest

from tests.conftest import ORIGIN, TOPIC_URL, bearer, make_token


def last_request(route) -> httpx.Request:
    return route.calls.last.request


# ---------- routing and auth ----------

@pytest.mark.parametrize("path", ["/nope", "/", "/api/v1/topicsX", "/api/v1/ai/anything", "/actuator/health"])
def test_unrouted_paths_are_404_with_cors_headers(client, upstream, path):
    route = upstream.route().respond(200)
    resp = client.get(path, headers={**bearer(), "Origin": ORIGIN})
    assert resp.status_code == 404
    assert resp.json() == {"error": {"code": "NOT_FOUND", "message": "No route"}}
    assert resp.headers["access-control-allow-origin"] == ORIGIN
    assert not route.called


def test_dot_segments_cannot_smuggle_a_protected_path_through_a_public_prefix(client, upstream):
    route = upstream.route().respond(200)
    resp = client.get("/oauth2/%2e%2e/api/v1/users/me")
    assert resp.status_code == 404
    assert not route.called


def test_public_routes_need_no_token(client, upstream):
    user = upstream.route(host="user.test").respond(200, json={"ok": True})
    for path in ("/api/v1/auth/login", "/oauth2/authorization/google", "/login/oauth2/code/google"):
        assert client.get(path).status_code == 200
    assert user.call_count == 3


@pytest.mark.parametrize("path", ["/api/v1/auth", "/api/v1/users/me", "/api/v1/topics", "/api/v1/sessions/1"])
def test_protected_routes_need_a_token(client, upstream, path):
    route = upstream.route().respond(200)
    assert client.get(path).status_code == 401
    assert not route.called


def test_user_and_topic_routes_go_to_the_right_upstream(client, upstream):
    user = upstream.route(host="user.test").respond(200, json={"from": "user"})
    topic = upstream.route(host="topic.test").respond(200, json={"from": "topic"})
    assert client.get("/api/v1/users/me", headers=bearer()).json() == {"from": "user"}
    assert client.get("/api/v1/topics", headers=bearer()).json() == {"from": "topic"}
    assert client.get("/api/v1/sessions/1", headers=bearer()).json() == {"from": "topic"}
    assert client.get("/api/v1/reports/1", headers=bearer()).json() == {"from": "topic"}
    assert (user.call_count, topic.call_count) == (1, 3)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Token abc"},
        {"Authorization": "Bearer not-a-jwt"},
        bearer(make_token(exp=1)),
        bearer(make_token(userId=...)),
        bearer(make_token(secret="another-secret-that-is-at-least-32-bytes!!")),
    ],
    ids=["missing", "wrong-scheme", "garbage", "expired", "no-userid", "wrong-secret"],
)
def test_401_has_the_error_envelope_and_cors_headers(client, upstream, headers):
    route = upstream.route().respond(200)
    resp = client.get("/api/v1/users/me", headers={**headers, "Origin": ORIGIN})
    assert resp.status_code == 401
    assert resp.json() == {"error": {"code": "USER_UNAUTHORIZED", "message": "Unauthorized"}}
    # without these the browser hides the 401 from axios and the silent refresh never fires
    assert resp.headers["access-control-allow-origin"] == ORIGIN
    assert resp.headers["access-control-allow-credentials"] == "true"
    assert not route.called


@pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512"])
def test_tokens_of_any_hmac_strength_are_accepted(client, upstream, algorithm):
    upstream.route().respond(200)
    assert client.get("/api/v1/users/me", headers=bearer(make_token(algorithm=algorithm))).status_code == 200


# ---------- trust headers ----------

def test_user_headers_are_injected_from_the_token(client, upstream):
    route = upstream.route().respond(200)
    client.get("/api/v1/users/me", headers=bearer(make_token(userId="user-123", email="me@example.com")))
    sent = last_request(route)
    assert sent.headers["x-user-id"] == "user-123"
    assert sent.headers["x-user-email"] == "me@example.com"


def test_missing_email_claim_is_forwarded_as_empty(client, upstream):
    route = upstream.route().respond(200)
    client.get("/api/v1/users/me", headers=bearer(make_token(email=...)))
    assert last_request(route).headers["x-user-email"] == ""


def test_spoofed_trust_headers_are_stripped_on_a_protected_route(client, upstream):
    route = upstream.route().respond(200)
    client.get(
        "/api/v1/users/me",
        headers={
            **bearer(make_token(userId="real-user", email="real@example.com")),
            "X-User-Id": "attacker",
            "X-User-Email": "attacker@example.com",
            "X-Internal-Api-Key": "stolen-key",
        },
    )
    sent = last_request(route)
    assert sent.headers.get_list("x-user-id") == ["real-user"]
    assert sent.headers.get_list("x-user-email") == ["real@example.com"]
    assert "x-internal-api-key" not in sent.headers


def test_spoofed_trust_headers_are_stripped_on_a_public_route_too(client, upstream):
    route = upstream.route().respond(200)
    client.post(
        "/api/v1/auth/login",
        json={},
        headers={"X-User-Id": "attacker", "X-User-Email": "a@b.c", "x-internal-api-key": "k"},
    )
    sent = last_request(route)
    assert "x-user-id" not in sent.headers
    assert "x-user-email" not in sent.headers
    assert "x-internal-api-key" not in sent.headers


def test_trust_headers_are_stripped_case_insensitively(client, upstream):
    route = upstream.route().respond(200)
    client.get("/oauth2/authorization/google", headers={"x-USER-id": "attacker", "X-INTERNAL-API-KEY": "k"})
    sent = last_request(route)
    assert "x-user-id" not in sent.headers and "x-internal-api-key" not in sent.headers


# ---------- request forwarding ----------

def test_method_path_query_and_body_are_forwarded_unchanged(client, upstream):
    route = upstream.route().respond(201, json={"id": "x"})
    body = b'{"name": "C++ \\u00e9", "n": 1}'
    resp = client.post(
        "/api/v1/topics?a=1&a=2&q=hello%20world%2B&empty=",
        content=body,
        headers={**bearer(), "Content-Type": "application/json"},
    )
    assert resp.status_code == 201
    sent = last_request(route)
    assert sent.method == "POST"
    assert str(sent.url) == f"{TOPIC_URL}/api/v1/topics?a=1&a=2&q=hello%20world%2B&empty="
    assert sent.content == body
    assert sent.headers["content-type"] == "application/json"


def test_percent_encoded_path_is_forwarded_raw(client, upstream):
    route = upstream.route().respond(200)
    client.get("/api/v1/topics/a%20b%2Fc", headers=bearer())
    assert last_request(route).url.raw_path == b"/api/v1/topics/a%20b%2Fc"


def test_binary_body_is_not_altered(client, upstream):
    route = upstream.route().respond(200)
    payload = bytes(range(256)) * 4
    client.post("/api/v1/topics", content=payload, headers={**bearer(), "Content-Type": "application/octet-stream"})
    assert last_request(route).content == payload


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_methods_are_forwarded(client, upstream, method):
    route = upstream.route().respond(200)
    client.request(method, "/api/v1/topics", headers=bearer())
    assert last_request(route).method == method


def test_authorization_and_cookie_are_forwarded(client, upstream):
    route = upstream.route().respond(200)
    token = make_token()
    client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": "refresh_token=abc; other=1", "Authorization": f"Bearer {token}"},
    )
    sent = last_request(route)
    assert sent.headers["cookie"] == "refresh_token=abc; other=1"
    assert sent.headers["authorization"] == f"Bearer {token}"


def test_hop_by_hop_and_host_headers_are_dropped(client, upstream):
    route = upstream.route().respond(200)
    client.get(
        "/api/v1/topics",
        headers={**bearer(), "Connection": "close", "Keep-Alive": "timeout=5", "TE": "trailers",
                 "Upgrade": "websocket", "Proxy-Authorization": "x"},
    )
    sent = last_request(route)
    for name in ("keep-alive", "te", "upgrade", "proxy-authorization"):
        assert name not in sent.headers
    assert sent.headers["connection"] == "keep-alive"  # httpx's own for this hop, not the client's "close"
    assert sent.headers["host"] == "topic.test"  # the upstream's host, not "testserver"


def test_request_id_is_generated_forwarded_and_echoed(client, upstream):
    route = upstream.route().respond(200)
    resp = client.get("/api/v1/topics", headers=bearer())
    generated = last_request(route).headers["x-request-id"]
    assert len(generated) == 36 and resp.headers["x-request-id"] == generated


def test_client_supplied_request_id_is_kept_and_cannot_be_duplicated(client, upstream):
    route = upstream.route().respond(200)
    resp = client.get("/api/v1/topics", headers={**bearer(), "X-Request-Id": "trace-me-1"})
    assert last_request(route).headers.get_list("x-request-id") == ["trace-me-1"]
    assert resp.headers["x-request-id"] == "trace-me-1"


# ---------- response forwarding ----------

def test_status_body_and_content_type_pass_through(client, upstream):
    upstream.route().respond(409, json={"error": {"code": "DUPLICATE_TOPIC", "message": "dup"}})
    resp = client.post("/api/v1/topics", json={}, headers=bearer())
    assert resp.status_code == 409
    assert resp.headers["content-type"] == "application/json"
    assert resp.json()["error"]["code"] == "DUPLICATE_TOPIC"


def test_204_has_no_body(client, upstream):
    upstream.route().respond(204)
    resp = client.delete("/api/v1/topics/x", headers=bearer())
    assert resp.status_code == 204 and resp.content == b""


def test_repeated_set_cookie_headers_all_reach_the_client(client, upstream):
    upstream.route().respond(
        200,
        headers=[
            ("set-cookie", "refresh_token=abc; Path=/api/v1/auth/refresh; HttpOnly; Secure; Max-Age=2592000"),
            ("set-cookie", "oauth_state=; Path=/login/oauth2; Max-Age=0"),
        ],
    )
    resp = client.post("/api/v1/auth/login", json={})
    cookies = resp.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert cookies[0].startswith("refresh_token=abc") and cookies[1].startswith("oauth_state=")


@pytest.mark.parametrize("location", ["/oauth2/authorization/google", "https://accounts.google.com/o/oauth2/v2/auth?x=1"])
def test_redirects_are_not_followed_and_location_is_untouched(client, upstream, location):
    follow_up = upstream.route(host="accounts.google.com").respond(200)
    upstream.route(host="user.test").respond(302, headers={"Location": location})
    resp = client.get("/api/v1/auth/google")
    assert resp.status_code == 302
    assert resp.headers["location"] == location
    assert not follow_up.called


def test_fragment_redirect_survives(client, upstream):
    target = "http://localhost:3000/auth/callback#token=abc.def.ghi"
    upstream.route().respond(302, headers={"Location": target})
    assert client.get("/login/oauth2/code/google?code=c&state=s").headers["location"] == target


def test_upstream_cors_headers_are_not_passed_through(client, upstream):
    upstream.route().respond(
        200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "false"}
    )
    no_origin = client.get("/api/v1/topics", headers=bearer())
    assert "access-control-allow-origin" not in no_origin.headers
    with_origin = client.get("/api/v1/topics", headers={**bearer(), "Origin": ORIGIN})
    assert with_origin.headers.get_list("access-control-allow-origin") == [ORIGIN]
    assert with_origin.headers.get_list("access-control-allow-credentials") == ["true"]


def test_upstream_server_and_date_headers_are_not_duplicated(client, upstream):
    upstream.route().respond(200, headers={"Server": "Spring", "Date": "Mon, 01 Jan 2001 00:00:00 GMT"})
    resp = client.get("/api/v1/topics", headers=bearer())
    assert len(resp.headers.get_list("date")) <= 1
    assert "spring" not in resp.headers.get("server", "").lower()


def test_sse_headers_pass_through(client, upstream):
    upstream.route().respond(
        200,
        content=b'data: {"token": "hi"}\n\ndata: [DONE]\n\n',
        headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    resp = client.post("/api/v1/topics/t/chat/messages", json={"content": "x"}, headers=bearer())
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.headers["x-accel-buffering"] == "no"
    assert resp.content == b'data: {"token": "hi"}\n\ndata: [DONE]\n\n'


# ---------- upstream failures ----------

@pytest.mark.parametrize("error", [httpx.ConnectError("refused"), httpx.ConnectTimeout("slow connect")])
def test_unreachable_upstream_is_502_with_cors_headers(client, upstream, error):
    upstream.route().mock(side_effect=error)
    resp = client.get("/api/v1/topics", headers={**bearer(), "Origin": ORIGIN})
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_upstream_timeout_before_response_is_504(client, upstream):
    upstream.route().mock(side_effect=httpx.ReadTimeout("too slow"))
    resp = client.get("/api/v1/topics", headers={**bearer(), "Origin": ORIGIN})
    assert resp.status_code == 504
    assert resp.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_protocol_errors_are_502(client, upstream):
    upstream.route().mock(side_effect=httpx.RemoteProtocolError("bad frame"))
    assert client.get("/api/v1/topics", headers=bearer()).status_code == 502


# ---------- CORS ----------

def test_preflight_is_answered_without_auth_or_upstream(client, upstream):
    route = upstream.route().respond(500)
    resp = client.options(
        "/api/v1/topics",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ORIGIN
    assert resp.headers["access-control-allow-credentials"] == "true"
    allowed = {m.strip() for m in resp.headers["access-control-allow-methods"].split(",")}
    assert allowed == {"GET", "POST", "PUT", "DELETE", "OPTIONS"}
    assert "authorization" in resp.headers["access-control-allow-headers"].lower()
    assert not route.called


def test_preflight_from_a_foreign_origin_is_refused(client):
    resp = client.options(
        "/api/v1/topics", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


def test_simple_response_to_foreign_origin_gets_no_cors_header(client, upstream):
    upstream.route().respond(200)
    resp = client.get("/api/v1/topics", headers={**bearer(), "Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in resp.headers


def test_multiple_origins_are_supported(upstream, monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "frontend_origin", "http://localhost:3000, https://app.example.com")
    upstream.route().respond(200)
    with TestClient(create_app()) as multi:
        for origin in ("http://localhost:3000", "https://app.example.com"):
            resp = multi.get("/api/v1/topics", headers={**bearer(), "Origin": origin})
            assert resp.headers["access-control-allow-origin"] == origin
