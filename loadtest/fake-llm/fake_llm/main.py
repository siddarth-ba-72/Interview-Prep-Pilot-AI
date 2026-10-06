"""An OpenAI-compatible chat completions server that answers like an LLM, for load testing.

ai-service reaches it through OPENAI_BASE_URL, so ai-service's own code - prompts, parsing,
retries - stays in the request path and only the model is swapped. Replies come from the
hardcoded banks in content.py; timing follows a model of time to first token plus tokens per
second (config.py).

Endpoints:
  POST /v1/chat/completions   streaming and non-streaming, as the OpenAI API
  GET  /v1/models             the model list, for clients that check it
  GET  /health
  GET  /stats                 requests per scenario and outcome, in-flight, tokens
  POST /admin/reset-stats
  GET  /admin/config          current knobs
  PATCH /admin/config         change knobs while running, e.g. {"error_rate": 0.1}
"""

import asyncio
import json
import logging
import random
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from fake_llm import scenarios
from fake_llm.config import Settings

app = FastAPI(title="PrepPilot fake LLM", version="1.0.0")

settings = Settings.from_env()
rng = random.Random(settings.seed)


class SimulatedDisconnect(Exception):
    """Raised inside a stream to cut it off, the way a dropped connection would."""


class _HideSimulatedDisconnects(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.exc_info and isinstance(record.exc_info[1], SimulatedDisconnect))


logging.getLogger("uvicorn.error").addFilter(_HideSimulatedDisconnects())


# --------------------------------------------------------------------------------------------
# Stats
# --------------------------------------------------------------------------------------------

class Stats:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.started_at = time.time()
        self.requests = 0
        self.in_flight = 0
        self.peak_in_flight = 0
        self.by_scenario: Counter = Counter()
        self.by_outcome: Counter = Counter()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.bad_json_sent = 0

    def begin(self, scenario: str) -> None:
        self.requests += 1
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        self.by_scenario[scenario] += 1

    def end(self, outcome: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        self.in_flight -= 1
        self.by_outcome[outcome] += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

    def snapshot(self) -> dict:
        uptime = max(time.time() - self.started_at, 1e-9)
        return {
            "uptime_seconds": round(uptime, 1),
            "requests": self.requests,
            "requests_per_second": round(self.requests / uptime, 2),
            "in_flight": self.in_flight,
            "peak_in_flight": self.peak_in_flight,
            "by_scenario": dict(self.by_scenario),
            "by_outcome": dict(self.by_outcome),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "bad_json_sent": self.bad_json_sent,
        }


stats = Stats()


# --------------------------------------------------------------------------------------------
# Timing
# --------------------------------------------------------------------------------------------

@dataclass
class Timing:
    first_token: float  # seconds until the first token
    per_token: float  # seconds between tokens


def _plan_timing(prompt_tokens: int) -> Timing:
    ttft = rng.uniform(settings.ttft_min_ms, max(settings.ttft_min_ms, settings.ttft_max_ms)) / 1000
    ttft += prompt_tokens * settings.prompt_ms_per_token / 1000
    if rng.random() < settings.slow_rate:
        ttft *= rng.uniform(3, 8)
    tokens_per_sec = max(rng.uniform(settings.tokens_per_sec_min, settings.tokens_per_sec_max), 1)
    return Timing(ttft * settings.latency_scale, settings.latency_scale / tokens_per_sec)


# Roughly how a BPE tokenizer splits English: short words whole (with their leading space), long
# words in pieces, punctuation on its own. Joining the pieces gives back the exact text.
_TOKEN_RE = re.compile(r"\s*[A-Za-z]{1,7}|\s*\d{1,3}|\s*[^\sA-Za-z\d]|\s+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _prompt_tokens(messages: list[dict]) -> int:
    return sum(len(str(m.get("content") or "")) // 4 + 4 for m in messages)


# --------------------------------------------------------------------------------------------
# OpenAI wire format
# --------------------------------------------------------------------------------------------

def _openai_error(status: int, message: str, error_type: str, code: str | None, headers: dict | None = None):
    body = {"error": {"message": message, "type": error_type, "param": None, "code": code}}
    return JSONResponse(status_code=status, content=body, headers=headers)


def _chunk(completion_id: str, created: int, model: str, delta: dict, finish_reason: str | None = None) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "system_fingerprint": "fp_fake_llm",
        "choices": [{"index": 0, "delta": delta, "logprobs": None, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _usage(prompt_tokens: int, completion_tokens: int) -> dict:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _make_bad_json(text: str) -> str:
    if rng.random() < 0.5:
        return f"Here is the JSON you asked for:\n\n```json\n{text}\n```\n\nLet me know if you need any changes."
    return text[: int(len(text) * rng.uniform(0.5, 0.9))]


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    if settings.api_key and request.headers.get("authorization") != f"Bearer {settings.api_key}":
        return _openai_error(401, "Incorrect API key provided (fake LLM).", "invalid_request_error", "invalid_api_key")

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _openai_error(400, "We could not parse the JSON body of your request.", "invalid_request_error", None)
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return _openai_error(400, "'messages' must be a non-empty array.", "invalid_request_error", None)

    model = body.get("model") or "gpt-4o-mini"
    stream = bool(body.get("stream"))
    json_mode = (body.get("response_format") or {}).get("type") == "json_object"
    include_usage = bool((body.get("stream_options") or {}).get("include_usage"))

    reply = scenarios.respond(messages, rng, json_mode=json_mode)
    prompt_tokens = _prompt_tokens(messages)
    stats.begin(reply.scenario)

    if rng.random() < settings.rate_limit_rate:
        stats.end("rate_limited")
        return _openai_error(
            429,
            f"Rate limit reached for {model} on tokens per min (TPM). Please try again in 1s. (simulated by fake LLM)",
            "tokens",
            "rate_limit_exceeded",
            headers={"retry-after": "1", "x-ratelimit-remaining-requests": "0"},
        )

    timing = _plan_timing(prompt_tokens)

    if rng.random() < settings.error_rate:
        try:
            await asyncio.sleep(timing.first_token)
        finally:
            stats.end("server_error")
        return _openai_error(500, "The server had an error while processing your request. (simulated by fake LLM)", "server_error", None)

    text = reply.text
    if reply.is_json and rng.random() < settings.bad_json_rate:
        text = _make_bad_json(text)
        stats.bad_json_sent += 1

    completion_id = f"chatcmpl-fake{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    pieces = _tokenize(text)

    if not stream:
        try:
            await asyncio.sleep(timing.first_token + len(pieces) * timing.per_token)
        except asyncio.CancelledError:
            stats.end("client_disconnected")
            raise
        stats.end("ok", prompt_tokens, len(pieces))
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "system_fingerprint": "fp_fake_llm",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text, "refusal": None},
                "logprobs": None,
                "finish_reason": "stop",
            }],
            "usage": _usage(prompt_tokens, len(pieces)),
        }

    drop_at = int(len(pieces) * rng.uniform(0.3, 0.7)) if rng.random() < settings.stream_drop_rate else None

    async def events():
        outcome, sent = "client_disconnected", 0
        try:
            await asyncio.sleep(timing.first_token)
            yield _chunk(completion_id, created, model, {"role": "assistant", "content": "", "refusal": None})

            loop = asyncio.get_running_loop()
            started = loop.time()
            tick = settings.stream_tick_ms / 1000
            while sent < len(pieces):
                if timing.per_token > 0:
                    due = int((loop.time() - started) / timing.per_token) + 1
                    due = min(len(pieces), max(due, sent + 1))
                else:
                    due = len(pieces)
                if drop_at is not None and due >= drop_at:
                    yield "".join(_chunk(completion_id, created, model, {"content": p}) for p in pieces[sent:drop_at])
                    sent = drop_at
                    outcome = "stream_dropped"
                    raise SimulatedDisconnect()
                yield "".join(_chunk(completion_id, created, model, {"content": p}) for p in pieces[sent:due])
                sent = due
                if sent < len(pieces):
                    await asyncio.sleep(max(tick, timing.per_token))

            final = _chunk(completion_id, created, model, {}, finish_reason="stop")
            if include_usage:
                usage_payload = {
                    "id": completion_id, "object": "chat.completion.chunk", "created": created, "model": model,
                    "system_fingerprint": "fp_fake_llm", "choices": [], "usage": _usage(prompt_tokens, len(pieces)),
                }
                final += f"data: {json.dumps(usage_payload, separators=(',', ':'))}\n\n"
            yield final + "data: [DONE]\n\n"
            outcome = "ok"
        finally:
            stats.end(outcome, prompt_tokens if outcome == "ok" else 0, sent)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"cache-control": "no-cache"})


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": name, "object": "model", "created": 1715367049, "owned_by": "preppilot-fake-llm"}
            for name in ("gpt-4o-mini", "gpt-4o")
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def get_stats():
    return stats.snapshot()


@app.post("/admin/reset-stats")
def reset_stats():
    stats.reset()
    return stats.snapshot()


@app.get("/admin/config")
def get_config():
    return settings.public()


@app.patch("/admin/config")
async def patch_config(request: Request):
    global settings, rng
    try:
        changes = await request.json()
        if not isinstance(changes, dict):
            raise ValueError("Send a JSON object of settings to change")
        settings = settings.updated(changes)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "seed" in changes:
        rng = random.Random(settings.seed)
    return settings.public()
