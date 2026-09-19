import json
import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

# Some model/proxy combinations reject these optional params. We probe once, and if the
# provider complains we remember it and stop sending them for the rest of the process.
_supports_json_mode = True
_supports_temperature = True


class LlmJsonError(RuntimeError):
    """Raised when the model could not be coaxed into returning parseable JSON."""


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
    return _client


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def extract_json_object(text: str) -> str:
    """Best-effort isolation of a single JSON object from a model response.

    Handles the two ways models commonly break the "return only JSON" contract:
    wrapping it in markdown fences, and prefixing/suffixing it with prose.
    """
    candidate = _strip_markdown_fences(text)
    if candidate.startswith("{") and candidate.endswith("}"):
        return candidate

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end > start:
        return candidate[start:end + 1]
    return candidate


async def _create_completion(messages: list[dict], *, json_mode: bool, temperature: float | None):
    """Call the chat completions API, degrading gracefully if the provider rejects
    response_format or temperature rather than failing the whole request."""
    global _supports_json_mode, _supports_temperature

    kwargs: dict = {"model": settings.llm_model, "messages": messages}
    if json_mode and _supports_json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if temperature is not None and _supports_temperature:
        kwargs["temperature"] = temperature

    client = get_client()
    try:
        return await client.chat.completions.create(**kwargs)
    except Exception as exc:
        detail = str(exc).lower()
        if "response_format" in detail and "response_format" in kwargs:
            logger.warning("Model %s rejected response_format; disabling JSON mode", settings.llm_model)
            _supports_json_mode = False
            return await _create_completion(messages, json_mode=False, temperature=temperature)
        if "temperature" in detail and "temperature" in kwargs:
            logger.warning("Model %s rejected temperature; falling back to the default", settings.llm_model)
            _supports_temperature = False
            return await _create_completion(messages, json_mode=json_mode, temperature=None)
        raise


async def call_llm(messages: list[dict]) -> str:
    """Call LLM and return full response text, stripping markdown code fences."""
    response = await _create_completion(messages, json_mode=False, temperature=None)
    return _strip_markdown_fences(response.choices[0].message.content or "")


async def call_llm_json(messages: list[dict], *, attempts: int = 3, temperature: float | None = 0.6) -> dict:
    """Call the LLM and return a parsed JSON object.

    Unlike `call_llm` + `json.loads`, this asks the provider for JSON mode and, when the
    response still isn't parseable, feeds the bad output back with a repair instruction.
    A malformed reply is the single most common cause of an interview turn failing, so it
    is worth the extra round-trip before surfacing an error to the caller.
    """
    conversation = list(messages)
    last_error = "no response"

    for attempt in range(1, attempts + 1):
        response = await _create_completion(conversation, json_mode=True, temperature=temperature)
        raw = response.choices[0].message.content or ""

        try:
            parsed = json.loads(extract_json_object(raw))
        except json.JSONDecodeError as exc:
            last_error = f"invalid JSON ({exc.msg})"
        else:
            if isinstance(parsed, dict):
                return parsed
            last_error = f"expected a JSON object, got {type(parsed).__name__}"

        logger.warning("LLM JSON parse failed on attempt %s/%s: %s", attempt, attempts, last_error)
        if attempt == attempts:
            break

        conversation = list(messages) + [
            {"role": "assistant", "content": raw[:4000]},
            {
                "role": "user",
                "content": (
                    f"Your previous response could not be parsed: {last_error}. "
                    "Respond again with ONLY the raw JSON object described above - no markdown "
                    "fences, no commentary before or after it."
                ),
            },
        ]

    raise LlmJsonError(f"Model did not return valid JSON after {attempts} attempts: {last_error}")


async def stream_completion(messages: list[dict]) -> AsyncGenerator[str, None]:
    client = get_client()
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
