import logging
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(error_body(code, message), status_code=status_code)


_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = errors[0]["msg"] if errors else "Invalid request"
        return error_response(400, "USER_INVALID_INPUT", message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        return error_response(500, "SYSTEM_INTERNAL_ERROR", "Internal server error")


class ErrorCode(Enum):
    """Port of Java's ErrorCode plus the ad-hoc string codes the Java services used and the D3 additions.

    Each member is (HTTP status, default message).
    """

    USER_INVALID_INPUT = (400, "Invalid input provided")
    USER_INVALID_TOPIC = (400, "Invalid topic provided")
    USER_INVALID_CONFIG = (400, "Invalid configuration")
    USER_UNAUTHORIZED = (401, "Unauthorized access")

    TOPIC_NOT_FOUND = (404, "Topic not found")
    CHAT_SESSION_NOT_FOUND = (404, "Chat session not found")
    MOCK_INTERVIEW_NOT_FOUND = (404, "Mock interview not found")

    AI_SERVICE_ERROR = (502, "AI service error")
    AI_INVALID_REQUEST = (400, "Invalid request for AI service")
    AI_SERVICE_UNAVAILABLE = (502, "AI service temporarily unavailable")

    SYSTEM_INTERNAL_ERROR = (500, "Internal server error")
    STREAMING_ERROR = (500, "Error during streaming operation")

    # Ad-hoc codes the Java services raised as plain strings
    DUPLICATE_TOPIC = (409, "Topic already exists")
    INVALID_INTERVIEW_CONFIG = (400, "Invalid interview configuration")
    INTERVIEW_ALREADY_COMPLETED = (409, "This interview has already been completed.")
    NO_ACTIVE_QUESTION = (409, "There is no question awaiting an answer on this interview.")
    INTERVIEW_NOT_COMPLETED = (409, "This interview is still in progress - no report has been generated yet.")

    # New in this port (deviation D3): Java answered these with a generic 500
    TEST_NOT_FOUND = (404, "Test not found")
    TEST_ALREADY_COMPLETED = (409, "Test is already completed")
    TEST_REPORT_NOT_FOUND = (404, "Report not found")

    @property
    def status(self) -> int:
        return self.value[0]

    @property
    def default_message(self) -> str:
        return self.value[1]


def api_error(code: ErrorCode, message: str | None = None) -> ApiError:
    return ApiError(code.status, code.name, message if message is not None else code.default_message)


def topic_not_found(topic_id: str) -> ApiError:
    return api_error(ErrorCode.TOPIC_NOT_FOUND, f"Topic not found: {topic_id}")


def chat_session_not_found(topic_id: str) -> ApiError:
    return api_error(
        ErrorCode.CHAT_SESSION_NOT_FOUND, f"No chat session found for topic: {topic_id}. Open Learn Mode first."
    )


def duplicate_topic(name: str) -> ApiError:
    return api_error(ErrorCode.DUPLICATE_TOPIC, f"Topic already exists: {name}")
