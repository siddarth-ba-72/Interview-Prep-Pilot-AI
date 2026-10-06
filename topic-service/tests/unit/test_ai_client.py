import json

import httpx
import pytest
import respx

from app.clients.ai_client import AiClient, AiStreamError, AiUnavailableError
from app.errors import ApiError
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
    with pytest.raises(AiStreamError, match="AI Service returned 500 INTERNAL_SERVER_ERROR: kaboom"):
        await tokens(client)


@respx.mock
async def test_non_2xx_without_a_body(client):
    respx.post(URL).mock(return_value=httpx.Response(401))
    with pytest.raises(AiStreamError) as exc:
        await tokens(client)
    assert str(exc.value) == "AI Service returned 401 UNAUTHORIZED"


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


# ---------- Test Mode calls ----------

GENERATE_URL = "http://ai.test/ai/test/generate"
EVALUATE_URL = "http://ai.test/ai/test/evaluate"


@respx.mock
async def test_generate_test_request_shape_and_parsing(client):
    route = respx.post(GENERATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "questions": [
                    {"questionId": "q1", "section": "MCQ", "text": "T?", "options": ["a", "b"], "correctOption": "a",
                     "somethingNew": 1},
                    {"questionId": "q2", "section": "SUBJECTIVE", "text": "Explain", "modelAnswer": "because"},
                ]
            },
        )
    )
    token = request_id_context.set("req-9")
    try:
        result = await client.generate_test("Kafka", ["Basics"], None)
    finally:
        request_id_context.reset(token)
    request = route.calls.last.request
    assert json.loads(request.content) == {"topicName": "Kafka", "strengths": ["Basics"], "weaknesses": None}
    assert request.headers["x-internal-api-key"] == KEY and request.headers["x-request-id"] == "req-9"
    assert [q.question_id for q in result.questions] == ["q1", "q2"]
    assert result.questions[0].correct_option == "a" and result.questions[1].model_answer == "because"


@respx.mock
async def test_evaluate_answers_request_shape_and_parsing(client):
    route = respx.post(EVALUATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={"perQuestion": [{"questionId": "q1", "isCorrect": True, "evaluation": "good"}],
                  "strengths": ["x"], "weaknesses": []},
        )
    )
    answers = [{"questionId": "q1", "section": "MCQ", "question": "T?", "correctAnswer": "a", "userAnswer": None}]
    result = await client.evaluate_answers("Kafka", answers)
    assert json.loads(route.calls.last.request.content) == {"topicName": "Kafka", "answers": answers}
    assert result.per_question[0].is_correct is True and result.strengths == ["x"] and result.weaknesses == []


@pytest.mark.parametrize(
    "call, url, prefix",
    [("generate", GENERATE_URL, "Invalid test request"), ("evaluate", EVALUATE_URL, "Invalid evaluation request")],
)
@respx.mock
async def test_400_becomes_ai_invalid_request_with_the_detail(client, call, url, prefix):
    respx.post(url).mock(return_value=httpx.Response(400, json={"detail": "topicName is too long"}))
    with pytest.raises(ApiError) as exc:
        await (client.generate_test("K", None, None) if call == "generate" else client.evaluate_answers("K", []))
    assert (exc.value.status_code, exc.value.code) == (400, "AI_INVALID_REQUEST")
    assert exc.value.message == f"{prefix}: topicName is too long"


@respx.mock
async def test_400_without_a_json_detail_shows_the_raw_body(client):
    respx.post(GENERATE_URL).mock(return_value=httpx.Response(400, text="plain bad request"))
    with pytest.raises(ApiError) as exc:
        await client.generate_test("K", None, None)
    assert exc.value.message == "Invalid test request: plain bad request"


@respx.mock
async def test_400_with_json_but_no_detail_shows_the_raw_body(client):
    respx.post(GENERATE_URL).mock(return_value=httpx.Response(400, json={"error": "nope"}))
    with pytest.raises(ApiError) as exc:
        await client.generate_test("K", None, None)
    assert exc.value.message == 'Invalid test request: {"error":"nope"}'


@respx.mock
async def test_structured_detail_is_rendered_as_json(client):
    respx.post(GENERATE_URL).mock(return_value=httpx.Response(400, json={"detail": [{"msg": "bad"}]}))
    with pytest.raises(ApiError) as exc:
        await client.generate_test("K", None, None)
    assert exc.value.message == 'Invalid test request: [{"msg": "bad"}]'


@pytest.mark.parametrize(
    "status, text", [(500, "500 INTERNAL_SERVER_ERROR"), (502, "502 BAD_GATEWAY"), (404, "404 NOT_FOUND")]
)
@respx.mock
async def test_other_non_2xx_is_a_502(client, status, text):
    respx.post(EVALUATE_URL).mock(return_value=httpx.Response(status, text="whatever"))
    with pytest.raises(ApiError) as exc:
        await client.evaluate_answers("K", [])
    assert (exc.value.status_code, exc.value.code) == (502, "AI_SERVICE_ERROR")
    assert exc.value.message == f"AI Service error: {text}"


@pytest.mark.parametrize(
    "error", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow"), httpx.RemoteProtocolError("x")]
)
@respx.mock
async def test_unreachable_or_timed_out_is_ai_service_unavailable(client, error):
    respx.post(GENERATE_URL).mock(side_effect=error)
    with pytest.raises(ApiError) as exc:
        await client.generate_test("K", None, None)
    assert (exc.value.status_code, exc.value.code) == (502, "AI_SERVICE_UNAVAILABLE")
    assert exc.value.message == "AI service temporarily unavailable"


@respx.mock
async def test_no_retry_on_failure(client):
    route = respx.post(GENERATE_URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ApiError):
        await client.generate_test("K", None, None)
    assert route.call_count == 1


@pytest.mark.parametrize(
    "body", ["not json at all", "[1, 2]", '{"questions": "nope"}', '{"questions": [{"options": "x"}]}']
)
@respx.mock
async def test_an_unusable_response_body_is_a_502(client, body):
    respx.post(GENERATE_URL).mock(return_value=httpx.Response(200, text=body))
    with pytest.raises(ApiError) as exc:
        await client.generate_test("K", None, None)
    assert (exc.value.status_code, exc.value.code) == (502, "AI_SERVICE_ERROR")
    assert exc.value.message == "AI Service returned an invalid response"


@respx.mock
async def test_a_sparse_response_parses_with_every_field_optional(client):
    respx.post(EVALUATE_URL).mock(return_value=httpx.Response(200, json={}))
    result = await client.evaluate_answers("K", [])
    assert result.per_question is None and result.strengths is None
