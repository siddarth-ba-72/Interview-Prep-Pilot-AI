"""The fake must look like the OpenAI API to the official SDK, streamed and not."""

import asyncio
import json

import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from fake_llm import main as fake
from fake_llm.main import _tokenize

LEARN_MESSAGES = [
    {"role": "system", "content": "You are an expert technical interviewer and teacher."},
    {"role": "system", "content": 'First, decide: is "Kubernetes" - and the student\'s latest message below, if any - '
                                  'genuinely related? ... The student just selected the topic "Kubernetes" to learn.'},
]


def sdk_client(max_retries: int = 2) -> AsyncOpenAI:
    transport = httpx.ASGITransport(app=fake.app)
    return AsyncOpenAI(
        api_key="sk-fake",
        base_url="http://fake-llm/v1",
        max_retries=max_retries,
        http_client=httpx.AsyncClient(transport=transport, base_url="http://fake-llm"),
    )


def test_non_streaming_response_parses_with_the_sdk():
    async def run():
        response = await sdk_client().chat.completions.create(model="gpt-4o-mini", messages=LEARN_MESSAGES)
        assert response.object == "chat.completion"
        assert response.choices[0].finish_reason == "stop"
        assert "Kubernetes" in response.choices[0].message.content
        assert response.usage.completion_tokens > 20

    asyncio.run(run())


def test_streaming_response_parses_with_the_sdk():
    async def run():
        stream = await sdk_client().chat.completions.create(
            model="gpt-4o-mini", messages=LEARN_MESSAGES, stream=True, stream_options={"include_usage": True}
        )
        tokens, finish_reasons, usage = [], [], None
        async for chunk in stream:
            if chunk.usage:
                usage = chunk.usage
            for choice in chunk.choices:
                if choice.delta.content:
                    tokens.append(choice.delta.content)
                if choice.finish_reason:
                    finish_reasons.append(choice.finish_reason)
        assert len(tokens) > 20, "each token should arrive as its own chunk"
        assert "Kubernetes" in "".join(tokens)
        assert finish_reasons == ["stop"]
        assert usage is not None and usage.completion_tokens == len(tokens)

    asyncio.run(run())


def test_raw_stream_ends_with_done():
    with TestClient(fake.app) as client:
        response = client.post("/v1/chat/completions", json={"model": "gpt-4o-mini", "messages": LEARN_MESSAGES, "stream": True})
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [line[len("data: "):] for line in response.text.split("\n") if line.startswith("data: ")]
    assert events[-1] == "[DONE]"
    first = json.loads(events[0])
    assert first["choices"][0]["delta"]["role"] == "assistant"


def test_injected_rate_limit_is_an_openai_429():
    fake.settings = fake.settings.updated({"rate_limit_rate": 1})

    async def run():
        with pytest.raises(openai.RateLimitError):
            await sdk_client(max_retries=0).chat.completions.create(model="gpt-4o-mini", messages=LEARN_MESSAGES)

    asyncio.run(run())
    assert fake.stats.snapshot()["by_outcome"] == {"rate_limited": 1}


def test_injected_server_error_is_retried_by_the_sdk():
    fake.settings = fake.settings.updated({"error_rate": 1})

    async def run():
        with pytest.raises(openai.InternalServerError):
            await sdk_client(max_retries=1).chat.completions.create(model="gpt-4o-mini", messages=LEARN_MESSAGES)

    asyncio.run(run())
    assert fake.stats.snapshot()["by_outcome"] == {"server_error": 2}


def test_api_key_is_enforced_when_configured():
    fake.settings = fake.settings.updated({"api_key": "secret"})
    with TestClient(fake.app) as client:
        denied = client.post("/v1/chat/completions", json={"messages": LEARN_MESSAGES})
        allowed = client.post("/v1/chat/completions", json={"messages": LEARN_MESSAGES},
                              headers={"Authorization": "Bearer secret"})
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "invalid_api_key"
    assert allowed.status_code == 200


def test_admin_config_changes_and_validates_knobs():
    with TestClient(fake.app) as client:
        changed = client.patch("/admin/config", json={"error_rate": 0.25, "latency_scale": 0.5})
        unknown = client.patch("/admin/config", json={"not_a_knob": 1})
        out_of_range = client.patch("/admin/config", json={"error_rate": 2})
    assert changed.status_code == 200
    assert changed.json()["error_rate"] == 0.25
    assert unknown.status_code == 400
    assert out_of_range.status_code == 400


def test_stats_count_requests_by_scenario():
    with TestClient(fake.app) as client:
        client.post("/v1/chat/completions", json={"messages": LEARN_MESSAGES})
        stats = client.get("/stats").json()
    assert stats["by_scenario"] == {"learn_clarify": 1}
    assert stats["by_outcome"] == {"ok": 1}
    assert stats["in_flight"] == 0


@pytest.mark.parametrize("text", [
    "Hello, world!",
    "  leading spaces and a verylongidentifiername_with_underscores()\n\n```python\nx = {'a': 1}\n```\n",
    "Unicode: café, naïve, 日本語 - and digits 1234567.",
])
def test_tokenizer_round_trips_text(text):
    assert "".join(_tokenize(text)) == text
