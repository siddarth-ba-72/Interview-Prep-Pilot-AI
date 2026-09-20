import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.exceptions import AppException, ErrorCode
from app.logging_config import user_id_context

logger = logging.getLogger(__name__)


def create_error_response(code: str, message: str, status_code: int = 500):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_error_handlers(app: FastAPI):
    """Register global error handlers for FastAPI app"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        log_record = logging.LogRecord(
            name=logger.name,
            level=log_level,
            pathname="",
            lineno=0,
            msg=exc.code,
            args=(),
            exc_info=None,
        )
        log_record.context_data = {
            "error_code": exc.code,
            "message": exc.message,
            **(exc.context or {}),
        }
        logger.handle(log_record)
        return create_error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        message = exc.errors()[0]["msg"] if exc.errors() else "Validation failed"
        log_record = logging.LogRecord(
            name=logger.name,
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg=f"Validation error: {message}",
            args=(),
            exc_info=None,
        )
        log_record.context_data = {
            "error_code": ErrorCode.USER_INVALID_INPUT,
        }
        logger.handle(log_record)
        return create_error_response(
            ErrorCode.USER_INVALID_INPUT,
            f"Request validation failed: {message}",
            400,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        log_record = logging.LogRecord(
            name=logger.name,
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Unexpected error occurred",
            args=(),
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        log_record.context_data = {
            "error_type": type(exc).__name__,
            "error_code": ErrorCode.SYSTEM_INTERNAL_ERROR,
        }
        logger.handle(log_record)
        return create_error_response(
            ErrorCode.SYSTEM_INTERNAL_ERROR,
            "An unexpected error occurred. Please try again later.",
            500,
        )
