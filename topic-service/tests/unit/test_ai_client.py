import httpx
import pytest
import respx

from app.clients.ai_client import AiClient, AiStreamError, AiUnavailableError
from app.logging_config import request_id_context

URL = "http://ai.test/ai/learn/stream"
KEY = "test-internal-key"


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as http:
        yield AiClient(http, "http://ai.test/", KEY)


def sse(*frames: str, status=200) -> httpx.Response:
    body = "".join(f"data: {f}\n\n" for f in frames).encode()
    return httpx.Response(status, content=body, headers={"content-type": "text/event-stream"})


async def tokens(client, mode="FOLLOW_UP", messages=None):
    return [t async for t in client.stream_learn("Kafka", mode, messages or [])]


@respx.mock
async def test_yields_tokens_until_done(client):
    respx.post(URL).mock(return_value=sse('{"token": "Hel"}', '{"token": "lo"}', "[DONE]"))
    assert await tokens(client) == ["Hel", "lo"]


@respx.mock
async def test_nothing_after_done_is_read(client):
    respx.post(URL).mock(return_value=sse('{"token": "a"}', "[DONE]", '{"token": "ignored"}'))
    assert await tokens(client) == ["a"]


@respx.mock
async def test_eof_without_done_is_a_normal_completion(client):
    respx.post(URL).mock(return_value=sse('{"token": "a"}', '{"token": "b"}'))
    assert await tokens(client) == ["a", "b"]


@respx.mock
async def test_data_prefix_with_or_without_a_space(client):
    body = b'data:{"token": "x"}\n\ndata: {"token": "y"}\n\ndata:[DONE]\n\n'
    respx.post(URL).mock(return_value=httpx.Response(200, content=body))
    assert await tokens(client) == ["x", "y"]


@respx.mock
async def test_non_data_lines_and_unrelated_json_are_ignored(client):
    body = b': keep-alive\n\nevent: ping\nid: 7\ndata: {"progress": 1}\n\ndata: {"token": "ok"}\n\ndata: [DONE]\n\n'
    respx.post(URL).mock(return_value=httpx.Response(200, content=body))
    assert await tokens(client) == ["ok"]


@respx.mock
async def test_whitespace_in_tokens_is_preserved(client):
    frames = ('{"token": " leading"}', '{"token": "trailing "}', '{"token": "\\n"}', "[DONE]")
    respx.post(URL).mock(return_value=sse(*frames))
    assert await tokens(client) == [" leading", "trailing ", "\n"]


@respx.mock
async def test_error_event_raises_with_the_message(client):
    respx.post(URL).mock(return_value=sse('{"token": "a"}', '{"error": "model overloaded"}'))
    seen = []
    with pytest.raises(AiStreamError, match="model overloaded"):
        async for token in client.stream_learn("Kafka", "FOLLOW_UP", []):
            seen.append(token)
    assert seen == ["a"]  # tokens before the error were still delivered


@respx.mock
async def test_malformed_json_raises(client):
    respx.post(URL).mock(return_value=sse("{not json"))
    with pytest.raises(AiStreamError, match="Malformed response from AI Service"):
        await tokens(client)


@respx.mock
async def test_non_2xx_raises_with_status_and_body(client):
    respx.post(URL).mock(return_value=httpx.Response(500, text="kaboom"))
    with pytest.raises(AiStreamError, match="AI Service returned 500: kaboom"):
        await tokens(client)


@respx.mock
async def test_non_2xx_without_a_body(client):
    respx.post(URL).mock(return_value=httpx.Response(401))
    with pytest.raises(AiStreamError) as exc:
        await tokens(client)
    assert str(exc.value) == "AI Service returned 401"


@pytest.mark.parametrize(
    "error", [httpx.ConnectError("refused"), httpx.ReadTimeout("silent"), httpx.RemoteProtocolError("x")]
)
@respx.mock
async def test_transport_failures_are_unavailable(client, error):
    respx.post(URL).mock(side_effect=error)
    with pytest.raises(AiUnavailableError):
        await tokens(client)


@respx.mock
async def test_request_shape_and_auth_headers(client):
    route = respx.post(URL).mock(return_value=sse("[DONE]"))
    token = request_id_context.set("req-123")
    try:
        await tokens(client, mode="GENERATE_CONTENT", messages=[{"role": "USER", "content": "hi"}])
    finally:
        request_id_context.reset(token)
    request = route.calls.last.request
    assert request.headers["x-internal-api-key"] == KEY
    assert request.headers["x-request-id"] == "req-123"
    assert request.headers["accept"] == "text/event-stream"
    assert request.headers["content-type"] == "application/json"
    import json

    assert json.loads(request.content) == {
        "topicName": "Kafka", "mode": "GENERATE_CONTENT", "messages": [{"role": "USER", "content": "hi"}]
    }


@respx.mock
async def test_no_request_id_header_when_none_is_set(client):
    route = respx.post(URL).mock(return_value=sse("[DONE]"))
    await tokens(client)
    assert "x-request-id" not in route.calls.last.request.headers


@respx.mock
async def test_base_url_trailing_slash_is_handled(client):
    route = respx.post(URL).mock(return_value=sse("[DONE]"))
    await tokens(client)
    assert route.called  # "http://ai.test/" + "/ai/learn/stream" did not produce a double slash
