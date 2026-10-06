import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.logging_config import request_id_context

logger = logging.getLogger(__name__)

STREAM_TIMEOUT = httpx.Timeout(connect=5, read=90, write=30, pool=5)  # read = max silence between chunks


class AiStreamError(Exception):
    """The AI service answered, but with an error status or an error/garbled event."""


class AiUnavailableError(Exception):
    """The AI service could not be reached, or went silent past the timeout."""


class AiClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str, internal_api_key: str) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")
        self.internal_api_key = internal_api_key

    def _headers(self) -> dict[str, str]:
        headers = {"X-Internal-Api-Key": self.internal_api_key}
        if request_id := request_id_context.get():
            headers["X-Request-Id"] = request_id  # ai-service logs it: one request, followed end to end
        return headers

    async def stream_learn(self, topic_name: str, mode: str, messages: list[dict]) -> AsyncIterator[str]:
        """Yield Learn Mode tokens. Ends normally on [DONE] (or on EOF, as the Java client did)."""
        body = {"topicName": topic_name, "mode": mode, "messages": messages}
        headers = {**self._headers(), "Accept": "text/event-stream"}
        try:
            async with self.http.stream(
                "POST", f"{self.base_url}/ai/learn/stream", json=body, headers=headers, timeout=STREAM_TIMEOUT
            ) as response:
                if not response.is_success:
                    detail = (await response.aread()).decode("utf-8", errors="replace")
                    message = f"AI Service returned {response.status_code}" + (f": {detail}" if detail else "")
                    logger.error(message, extra={"topic": topic_name, "mode": mode})
                    raise AiStreamError(message)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].removeprefix(" ")
                    if data.strip() == "[DONE]":
                        return
                    if not data.strip():
                        continue
                    try:
                        node = json.loads(data)
                    except ValueError:
                        logger.error("Malformed response from AI Service", extra={"topic": topic_name})
                        raise AiStreamError("Malformed response from AI Service") from None
                    if not isinstance(node, dict):
                        continue
                    if "error" in node:
                        logger.error(f"AI error in stream: {node['error']}", extra={"topic": topic_name})
                        raise AiStreamError(str(node["error"]))
                    if "token" in node:
                        token = node["token"]
                        yield token if isinstance(token, str) else json.dumps(token)
        except httpx.HTTPError as exc:
            logger.error("AI service unreachable", extra={"topic": topic_name, "error": type(exc).__name__})
            raise AiUnavailableError(str(exc) or type(exc).__name__) from exc
