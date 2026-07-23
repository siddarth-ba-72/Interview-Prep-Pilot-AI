from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
    return _client


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
