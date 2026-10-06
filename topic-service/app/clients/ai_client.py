import asyncio
import json
import logging
from collections.abc import AsyncIterator
from http import HTTPStatus

import httpx
from pydantic import BaseModel, ValidationError

from app.clients.ai_schemas import (
    EvaluateAnswersResponse,
    GenerateInterviewReportRequest,
    GenerateInterviewReportResponse,
    GenerateTestResponse,
    NextTurnRequest,
    NextTurnResponse,
    PlanInterviewRequest,
    PlanInterviewResponse,
    ReportExchange,
)
from app.errors import ErrorCode, api_error
from app.logging_config import request_id_context

logger = logging.getLogger(__name__)

STREAM_TIMEOUT = httpx.Timeout(connect=5, read=90, write=30, pool=5)  # read = max silence between chunks
TEST_TIMEOUT = httpx.Timeout(connect=5, read=180, write=30, pool=5)  # generating/evaluating a whole test is slow
INTERVIEW_HTTP_TIMEOUT = httpx.Timeout(connect=5, read=90, write=30, pool=5)
INTERVIEW_CALL_TIMEOUT = 90  # seconds for the whole call, retry included: it is user-facing, so never hang


def status_text(code: int) -> str:
    """'500 INTERNAL_SERVER_ERROR', the way Spring prints an HttpStatusCode."""
    try:
        return f"{code} {HTTPStatus(code).name}"
    except ValueError:
        return str(code)


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
                    message = f"AI Service returned {status_text(response.status_code)}"
                    if detail:
                        message += f": {detail}"
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

    # ---------- Test Mode: plain request/response, no retry ----------

    async def generate_test(
        self, topic_name: str, strengths: list[str] | None, weaknesses: list[str] | None
    ) -> GenerateTestResponse:
        body = {"topicName": topic_name, "strengths": strengths, "weaknesses": weaknesses}
        data = await self._post_json("/ai/test/generate", body, TEST_TIMEOUT, "Invalid test request", topic_name)
        return _parse(GenerateTestResponse, data)

    async def evaluate_answers(self, topic_name: str, answers: list[dict]) -> EvaluateAnswersResponse:
        body = {"topicName": topic_name, "answers": answers}
        data = await self._post_json(
            "/ai/test/evaluate", body, TEST_TIMEOUT, "Invalid evaluation request", topic_name
        )
        return _parse(EvaluateAnswersResponse, data)

    async def _post_json(
        self, path: str, body: dict, timeout: httpx.Timeout, invalid_prefix: str, topic_name: str
    ) -> object:
        """POST and return the parsed JSON. Failures become ApiErrors, as in the Java AiClient."""
        try:
            response = await self.http.post(
                f"{self.base_url}{path}", json=body, headers=self._headers(), timeout=timeout
            )
        except httpx.HTTPError as exc:
            error = type(exc).__name__
            logger.error("AI service unreachable", extra={"path": path, "topic": topic_name, "error": error})
            raise api_error(ErrorCode.AI_SERVICE_UNAVAILABLE) from exc
        if response.status_code == 400:
            message = f"{invalid_prefix}: {_error_detail(response)}"
            logger.error(message, extra={"topic": topic_name})
            raise api_error(ErrorCode.AI_INVALID_REQUEST, message)
        if not response.is_success:
            message = f"AI Service error: {status_text(response.status_code)}"
            logger.error(message, extra={"topic": topic_name})
            raise api_error(ErrorCode.AI_SERVICE_ERROR, message)
        try:
            return response.json()
        except ValueError:
            logger.error("AI service returned a non-JSON body", extra={"path": path, "topic": topic_name})
            raise api_error(ErrorCode.AI_SERVICE_ERROR, "AI Service returned an invalid response") from None

    # ---------- Mock Interview ----------
    # Callers fall back to deterministic behaviour on any failure here, so these simply raise.

    async def plan_interview(
        self, topic_name: str, experience_level: str, difficulty: str, duration_minutes: int
    ) -> PlanInterviewResponse:
        request = PlanInterviewRequest(
            topic_name=topic_name,
            experience_level=experience_level,
            difficulty=difficulty,
            duration_minutes=duration_minutes,
        )
        return await self._post_interview("/ai/interview/plan", request, PlanInterviewResponse)

    async def next_turn(self, request: NextTurnRequest) -> NextTurnResponse:
        return await self._post_interview("/ai/interview/next-turn", request, NextTurnResponse)

    async def generate_interview_report(
        self, topic_name: str, experience_level: str, difficulty: str, exchanges: list[ReportExchange]
    ) -> GenerateInterviewReportResponse:
        request = GenerateInterviewReportRequest(
            topic_name=topic_name, experience_level=experience_level, difficulty=difficulty, exchanges=exchanges
        )
        return await self._post_interview("/ai/interview/generate-report", request, GenerateInterviewReportResponse)

    async def _post_interview[T: BaseModel](self, path: str, request: BaseModel, response_model: type[T]) -> T:
        payload = request.model_dump(by_alias=True)
        try:
            async with asyncio.timeout(INTERVIEW_CALL_TIMEOUT):
                response = await self._post_retrying_connect_failures(path, payload)
        except TimeoutError:
            logger.error("AI call timed out", extra={"path": path})
            raise api_error(ErrorCode.AI_SERVICE_UNAVAILABLE) from None
        except httpx.HTTPError as exc:
            logger.error("AI service unreachable", extra={"path": path, "error": type(exc).__name__})
            raise api_error(ErrorCode.AI_SERVICE_UNAVAILABLE) from exc

        body = response.text
        if response.status_code == 400:
            message = "Invalid AI request" + (f": {body}" if body else "")
            logger.error(message, extra={"endpoint": path})
            raise api_error(ErrorCode.AI_INVALID_REQUEST, message)
        if not response.is_success:
            message = f"AI Service error: {status_text(response.status_code)}" + (f" - {body}" if body else "")
            logger.error(message, extra={"endpoint": path})
            raise api_error(ErrorCode.AI_SERVICE_ERROR, message)
        try:
            data = response.json()
        except ValueError:
            raise api_error(ErrorCode.AI_SERVICE_ERROR, "AI Service returned an invalid response") from None
        return _parse(response_model, data)

    async def _post_retrying_connect_failures(self, path: str, payload: dict) -> httpx.Response:
        """One retry, and only when the connection itself failed: malformed-output retries live in ai-service,
        where the bad output can be fed back for repair. Retrying a slow call here would only multiply latency."""
        for attempt in (1, 2):
            try:
                return await self.http.post(
                    f"{self.base_url}{path}", json=payload, headers=self._headers(), timeout=INTERVIEW_HTTP_TIMEOUT
                )
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt == 2:
                    raise
                logger.warning("Could not reach the AI service, retrying once", extra={"path": path})
        raise AssertionError("unreachable")


def _error_detail(response: httpx.Response) -> str:
    """The `detail` of a JSON error body if there is one, otherwise the raw body."""
    text = response.text
    try:
        payload = json.loads(text)
    except ValueError:
        return text
    if isinstance(payload, dict) and payload.get("detail") is not None:
        detail = payload["detail"]
        return detail if isinstance(detail, str) else json.dumps(detail)
    return text


def _parse[T: BaseModel](model: type[T], data: object) -> T:
    try:
        return model.model_validate(data)
    except ValidationError:
        logger.error("AI service response did not match the expected shape", extra={"model": model.__name__})
        raise api_error(ErrorCode.AI_SERVICE_ERROR, "AI Service returned an invalid response") from None
