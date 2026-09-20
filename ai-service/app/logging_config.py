import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

user_id_context: ContextVar[str | None] = ContextVar("user_id", default=None)
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class StructuredJsonFormatter(logging.Formatter):
    """Formats logs as JSON with user context"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        user_id = user_id_context.get()
        if user_id:
            log_data["user_id"] = user_id

        request_id = request_id_context.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add context data if present
        if hasattr(record, "context_data") and record.context_data:
            log_data.update(record.context_data)

        # Don't include stack trace in JSON for normal logs
        # Only add exception type if there's an exception
        if record.exc_info:
            log_data["exception_type"] = record.exc_info[0].__name__
            log_data["exception_message"] = str(record.exc_info[1])

        try:
            return json.dumps(log_data)
        except (TypeError, ValueError):
            # Fallback if JSON encoding fails
            return str(log_data)


def setup_structured_logging():
    """Configure JSON structured logging for all loggers"""
    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredJsonFormatter()
    handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )

    # Suppress verbose uvicorn logs
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)
