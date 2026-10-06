import pytest

from app.routes import has_dot_segments, is_public, match


@pytest.mark.parametrize(
    "path, upstream",
    [
        ("/oauth2/authorization/google", "user"),
        ("/oauth2", "user"),
        ("/login/oauth2/code/google", "user"),
        ("/api/v1/auth/login", "user"),
        ("/api/v1/auth", "user"),
        ("/api/v1/users/me", "user"),
        ("/api/v1/topics", "topic"),
        ("/api/v1/topics/abc/chat/messages", "topic"),
        ("/api/v1/sessions/x", "topic"),
        ("/api/v1/reports/x", "topic"),
    ],
)
def test_routed_paths(path, upstream):
    route = match(path)
    assert route is not None and route.upstream == upstream


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/api/v1/topicsX",  # a prefix match, not a segment match
        "/api/v1/authX/login",
        "/api/v1/usersX",
        "/api/v1/ai/anything",  # D1: no longer routed
        "/api/v1/ai",
        "/api/v2/topics",
        "/oauth2x",
        "/health",  # answered by the gateway itself, never proxied
        "/actuator/health",
    ],
)
def test_unrouted_paths(path):
    assert match(path) is None


@pytest.mark.parametrize(
    "path, public",
    [
        ("/api/v1/auth/login", True),
        ("/api/v1/auth/", True),
        ("/api/v1/auth", False),  # routed, but not whitelisted: needs a JWT, exactly as in Spring
        ("/oauth2/authorization/google", True),
        ("/login/oauth2/code/google", True),
        ("/health", True),
        ("/api/v1/users/me", False),
        ("/api/v1/topics", False),
        ("/api/v1/sessions/1", False),
        ("/api/v1/reports/1", False),
    ],
)
def test_public_paths(path, public):
    assert is_public(path) is public


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("/api/v1/topics", False),
        ("/api/v1/topics/a.b", False),
        ("/api/v1/topics/..hidden", False),
        ("/oauth2/../api/v1/users/me", True),
        ("/oauth2/./x", True),
        ("/oauth2/%2e%2e/api/v1/users/me", True),
        ("/oauth2/%2E%2E/x", True),
        ("/oauth2/..%2fapi/x", True),
        ("/a/..", True),
    ],
)
def test_dot_segments(raw, expected):
    assert has_dot_segments(raw) is expected
