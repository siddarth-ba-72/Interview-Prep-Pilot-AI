from fastapi import Request

from app.errors import ApiError
from app.logging_config import user_id_context
from app.services.chat_service import ChatService
from app.services.topic_service import TopicService


def current_user_id(request: Request) -> str:
    """Only the gateway can reach this service, and it injects X-User-Id after verifying the JWT.
    Never read a user id from the body or the path."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise ApiError(401, "USER_UNAUTHORIZED", "Missing required header")
    user_id_context.set(user_id)
    return user_id


def get_topic_service(request: Request) -> TopicService:
    return request.app.state.topic_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
