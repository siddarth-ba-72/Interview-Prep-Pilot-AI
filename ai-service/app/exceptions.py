from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    # User errors (4xx)
    USER_INVALID_INPUT = "USER_INVALID_INPUT"
    USER_INVALID_TOPIC = "USER_INVALID_TOPIC"
    USER_INVALID_CONFIG = "USER_INVALID_CONFIG"
    USER_UNAUTHORIZED = "USER_UNAUTHORIZED"

    # System errors (5xx)
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"
    SYSTEM_TIMEOUT = "SYSTEM_TIMEOUT"
    SYSTEM_SERVICE_UNAVAILABLE = "SYSTEM_SERVICE_UNAVAILABLE"


class AppException(Exception):
    """Base exception class for application errors"""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        status_code: int = 500,
        context: dict[str, Any] | None = None,
    ):
        self.code = code if isinstance(code, str) else code.value
        self.message = message
        self.status_code = status_code
        self.context = context or {}
        super().__init__(self.message)


class ValidationError(AppException):
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(
            code=ErrorCode.USER_INVALID_INPUT,
            message=message,
            status_code=400,
            context=context,
        )


class InvalidTopicError(AppException):
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(
            code=ErrorCode.USER_INVALID_TOPIC,
            message=message,
            status_code=400,
            context=context,
        )


class InvalidConfigError(AppException):
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(
            code=ErrorCode.USER_INVALID_CONFIG,
            message=message,
            status_code=400,
            context=context,
        )
