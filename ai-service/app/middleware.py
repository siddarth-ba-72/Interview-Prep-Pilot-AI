import logging
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import user_id_context, request_id_context

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and store user context in context variables"""

    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-Id") or request.headers.get("x-user-id")
        request_id = (
            request.headers.get("X-Request-Id")
            or request.headers.get("x-request-id")
            or str(uuid.uuid4())
        )

        token_user = user_id_context.set(user_id)
        token_request = request_id_context.set(request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            user_id_context.reset(token_user)
            request_id_context.reset(token_request)
