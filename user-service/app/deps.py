from fastapi import Request

from app.errors import ApiError
from app.logging_config import user_id_context
from app.services.auth_service import AuthService
from app.services.google_oauth import GoogleOAuthClient
from app.services.user_service import UserService


def current_user_id(request: Request) -> str:
    """The gateway injects X-User-Id after verifying the JWT; this service is never exposed directly."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise ApiError(401, "USER_UNAUTHORIZED", "Missing required header")
    user_id_context.set(user_id)
    return user_id


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_user_service(request: Request) -> UserService:
    return request.app.state.user_service


def get_google_client(request: Request) -> GoogleOAuthClient:
    return request.app.state.google_client
