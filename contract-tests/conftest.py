"""Black-box contract tests that run against either backend through the gateway."""
import json
import os
import uuid
from http.cookies import SimpleCookie

import httpx
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
BACKEND = os.environ.get("BACKEND", "java").lower()
ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
PASSWORD = "Contract-Pass-123"

USER_PROFILE_KEYS = {"id", "email", "displayName"}
AUTH_RESPONSE_KEYS = {"accessToken", "user"}


def pytest_collection_modifyitems(config, items):
    if BACKEND == "python":
        return
    skip = pytest.mark.skip(reason="deliberate deviation (D1/D3/D4); only asserted when BACKEND=python")
    for item in items:
        if "python_only" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def http():
    # No redirects: OAuth tests assert on the raw 302. Generous timeout: AI-backed calls are slow.
    with httpx.Client(base_url=BASE_URL, follow_redirects=False, timeout=240) as client:
        yield client


def refresh_cookie_from(response: httpx.Response) -> tuple[str | None, str | None]:
    """Return (cookie value, raw Set-Cookie header) for refresh_token.

    httpx's cookie jar won't resend a Secure cookie over http://, so tests read the header and
    send `Cookie: refresh_token=<value>` by hand.
    """
    for raw in response.headers.get_list("set-cookie"):
        if raw.startswith("refresh_token="):
            jar = SimpleCookie()
            jar.load(raw)
            return jar["refresh_token"].value, raw
    return None, None


def new_email() -> str:
    return f"contract+{uuid.uuid4().hex}@example.com"


class Session:
    """A freshly registered and logged-in user."""

    def __init__(self, http: httpx.Client, email: str, access_token: str, user: dict, refresh: str):
        self.http = http
        self.email = email
        self.access_token = access_token
        self.user = user
        self.refresh = refresh

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = {**self.headers, **kwargs.pop("headers", {})}
        return self.http.request(method, path, headers=headers, **kwargs)

    def get(self, path: str, **kw):
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw):
        return self.request("POST", path, **kw)

    def delete(self, path: str, **kw):
        return self.request("DELETE", path, **kw)

    def sse(self, path: str, body: dict) -> list[str]:
        """POST and return the `data:` payloads of the event stream."""
        frames = []
        with self.http.stream("POST", path, headers=self.headers, json=body) as resp:
            assert resp.status_code == 200, resp.read()
            assert resp.headers["content-type"].startswith("text/event-stream")
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    frames.append(line[len("data:"):].removeprefix(" "))
        return frames


def make_session(http: httpx.Client) -> Session:
    email = new_email()
    reg = http.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD, "displayName": "Contract User"})
    assert reg.status_code == 201, reg.text
    login = http.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    body = login.json()
    refresh, _ = refresh_cookie_from(login)
    assert refresh, "login must set the refresh_token cookie"
    return Session(http, email, body["accessToken"], body["user"], refresh)


@pytest.fixture(scope="module")
def user(http) -> Session:
    return make_session(http)


@pytest.fixture(scope="module")
def other_user(http) -> Session:
    return make_session(http)


@pytest.fixture
def topic(user):
    """A throwaway topic owned by `user`; deleted afterwards."""
    resp = user.post("/api/v1/topics", json={"name": f"Contract {uuid.uuid4().hex[:8]}"})
    assert resp.status_code == 201, resp.text
    t = resp.json()
    yield t
    user.delete(f"/api/v1/topics/{t['id']}")


def parse_frames(frames: list[str]) -> list:
    """SSE payloads -> python objects; the sentinel stays the string '[DONE]'."""
    return [f if f == "[DONE]" else json.loads(f) for f in frames]
