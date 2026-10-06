"""Tuning knobs. Each one is read from an env var (FAKE_LLM_<NAME>) at startup and can be changed
while the server runs with `PATCH /admin/config`, e.g. to inject errors halfway through a load test.

The latency defaults are roughly what gpt-4o-mini looks like from a well-connected server:
under a second to the first token, then 60-110 tokens per second. Token counts are within ~10% of
gpt-4o's real tokenizer (o200k_base), so a reply takes about as long as the real one would.
"""

import os
from dataclasses import asdict, dataclass, fields, replace


@dataclass(frozen=True)
class Settings:
    # Multiplies every delay. 1.0 = realistic, 0.1 = ten times faster, 0 = no delays at all.
    latency_scale: float = 1.0
    # Time to first token, before the per-token time starts.
    ttft_min_ms: float = 350
    ttft_max_ms: float = 1200
    # Extra time to first token per prompt token: long prompts take longer to start.
    prompt_ms_per_token: float = 0.04
    # Output speed, picked per request.
    tokens_per_sec_min: float = 60
    tokens_per_sec_max: float = 110
    # A stream sends due tokens in one write at most every this many ms (each token is still its
    # own SSE event). This bounds the fake's own CPU use when thousands of streams are open.
    stream_tick_ms: float = 40
    # Share of requests whose time to first token is 3-8x longer, like a slow provider moment.
    slow_rate: float = 0.02
    # Failure injection, each a probability per request (0-1). The OpenAI SDK retries 429 and
    # 5xx twice by default, so a request only fails for good if every attempt fails.
    error_rate: float = 0.0
    rate_limit_rate: float = 0.0
    # Streams cut off partway through, like a dropped connection.
    stream_drop_rate: float = 0.0
    # JSON replies wrapped in prose and code fences, or truncated, as real models sometimes do.
    bad_json_rate: float = 0.0
    # When set, requests must send "Authorization: Bearer <api_key>".
    api_key: str = ""
    # Fixes the random choices (content and timing) for reproducible runs. Unset = random.
    seed: int | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        values = {}
        for field in fields(cls):
            raw = os.environ.get(f"FAKE_LLM_{field.name.upper()}")
            if raw not in (None, ""):
                values[field.name] = _convert(field.name, raw)
        return cls(**values)

    def updated(self, changes: dict) -> "Settings":
        known = {field.name for field in fields(self)}
        unknown = set(changes) - known
        if unknown:
            raise ValueError(f"Unknown setting(s): {', '.join(sorted(unknown))}")
        return replace(self, **{name: _convert(name, value) for name, value in changes.items()})

    def public(self) -> dict:
        values = asdict(self)
        values["api_key"] = "(set)" if self.api_key else ""
        return values


def _convert(name: str, value):
    if name == "api_key":
        return str(value)
    if name == "seed":
        return None if value in (None, "") else int(value)
    number = float(value)
    if number < 0:
        raise ValueError(f"{name} must not be negative")
    if name.endswith("_rate") and number > 1:
        raise ValueError(f"{name} is a probability between 0 and 1")
    return number
