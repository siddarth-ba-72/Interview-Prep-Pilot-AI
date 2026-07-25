from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


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


async def call_llm(messages: list[dict]) -> str:
    """Call LLM and return full response text, stripping markdown code fences."""
    client = get_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
    )
    return _strip_markdown_fences(response.choices[0].message.content)


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
