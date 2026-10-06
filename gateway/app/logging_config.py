import json
import logging
import sys
import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

user_id_context: ContextVar[str | None] = ContextVar("user_id", default=None)
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

REQUEST_ID_HEADER = "x-request-id"

# Attributes every LogRecord carries; anything else was passed through `extra=` and is logged as context.
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


class StructuredJsonFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger, message, service, request_id, user_id + extras."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
        }
        if request_id := request_id_context.get():
            data["request_id"] = request_id
        if user_id := user_id_context.get():
            data["user_id"] = user_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                data[key] = value
        if record.exc_info and record.exc_info[0]:
            data["exception_type"] = record.exc_info[0].__name__
            data["exception_message"] = str(record.exc_info[1])
        try:
            return json.dumps(data, default=str)
        except (TypeError, ValueError):
            return str(data)


def setup_structured_logging(service: str, level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter(service))
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.handlers = [handler]
        uv.propagate = False
        uv.setLevel(logging.WARNING)
    # httpx logs every outbound request at INFO; the proxy and AI client would drown the real logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)


class RequestIdMiddleware:
    """Reads X-Request-Id (or generates a UUID4), exposes it to log lines and echoes it on the response.

    Written as plain ASGI rather than BaseHTTPMiddleware so streaming (SSE) responses are never buffered.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for name, value in scope["headers"]:
            if name == REQUEST_ID_HEADER.encode():
                request_id = value.decode("latin-1").strip() or None
                break
        request_id = request_id or str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["X-Request-Id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_context.reset(token)
