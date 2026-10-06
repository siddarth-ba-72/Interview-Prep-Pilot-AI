"""SSE must be forwarded chunk by chunk. TestClient can't show this (it buffers whole responses), so these
tests run the gateway on a real uvicorn server and read the response incrementally."""
import asyncio
import threading
import time

import httpx
import pytest
import uvicorn

from app.main import create_app
from tests.conftest import bearer


class LiveServer:
    def __init__(self, app):
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started:
            assert time.time() < deadline, "server did not start"
            time.sleep(0.01)
        port = self.server.servers[0].sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        return self

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=10)


def test_first_chunk_arrives_before_the_upstream_finishes():
    state = {"finished": False}
    release = threading.Event()

    async def sse_stream():
        yield b'data: {"token": "one"}\n\n'
        deadline = time.time() + 5
        while not release.is_set() and time.time() < deadline:
            await asyncio.sleep(0.01)
        yield b'data: {"token": "two"}\n\n'
        yield b"data: [DONE]\n\n"
        state["finished"] = True

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, content=sse_stream())

    app = create_app(topic_transport=httpx.MockTransport(handler))
    with LiveServer(app) as live, httpx.Client(timeout=10) as http:
        with http.stream("POST", f"{live.url}/api/v1/topics/t/chat/messages", headers=bearer(), json={}) as resp:
            assert resp.status_code == 200
            chunks = resp.iter_raw()
            first = next(chunks)
            # A buffering proxy could only have produced this after the upstream had finished.
            assert first == b'data: {"token": "one"}\n\n'
            assert state["finished"] is False
            release.set()
            rest = b"".join(chunks)
        assert rest == b'data: {"token": "two"}\n\ndata: [DONE]\n\n'


def test_closing_the_client_early_closes_the_upstream_stream():
    closed = threading.Event()

    async def endless():
        try:
            while True:
                yield b"data: tick\n\n"
                await asyncio.sleep(0.02)
        finally:
            closed.set()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, content=endless())

    app = create_app(topic_transport=httpx.MockTransport(handler))
    with LiveServer(app) as live, httpx.Client(timeout=10) as http:
        with http.stream("GET", f"{live.url}/api/v1/topics/t/chat", headers=bearer()) as resp:
            next(resp.iter_raw())
        assert closed.wait(timeout=5), "upstream stream was not closed after the client went away"


def test_set_cookie_and_redirect_survive_a_real_server():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers=[
                ("Location", "http://localhost:3000/auth/callback#token=t"),
                ("Set-Cookie", "a=1"),
                ("Set-Cookie", "b=2"),
            ],
            stream=httpx.ByteStream(b""),  # a hand-built Response is "already read"; real transports hand back a stream
        )

    app = create_app(user_transport=httpx.MockTransport(handler))
    with LiveServer(app) as live, httpx.Client(follow_redirects=False) as http:
        resp = http.get(f"{live.url}/login/oauth2/code/google?code=c&state=s")
    assert resp.status_code == 302
    assert resp.headers["location"] == "http://localhost:3000/auth/callback#token=t"
    assert resp.headers.get_list("set-cookie") == ["a=1", "b=2"]


@pytest.mark.parametrize("path", ["/api/v1/users/me"])
def test_unauthorised_request_never_reaches_the_upstream_on_a_real_server(path):
    called = threading.Event()

    def handler(request: httpx.Request) -> httpx.Response:
        called.set()
        return httpx.Response(200)

    app = create_app(user_transport=httpx.MockTransport(handler))
    with LiveServer(app) as live, httpx.Client() as http:
        assert http.get(f"{live.url}{path}").status_code == 401
    assert not called.is_set()
