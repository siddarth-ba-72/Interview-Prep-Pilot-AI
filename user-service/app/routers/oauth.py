import hmac
import logging
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.deps import get_auth_service, get_google_client
from app.routers.cookies import (
    OAUTH_STATE_COOKIE,
    clear_oauth_state_cookie,
    set_oauth_state_cookie,
    set_refresh_cookie,
)
from app.services.auth_service import AuthService
from app.services.google_oauth import GoogleOAuthClient

logger = logging.getLogger(__name__)

router = APIRouter()


def _frontend() -> str:
    return settings.frontend_origin.rstrip("/")


@router.get("/oauth2/authorization/google")
async def authorize(google: GoogleOAuthClient = Depends(get_google_client)):
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(google.authorize_url(state), status_code=302)
    set_oauth_state_cookie(response, state)
    return response


def _failure() -> RedirectResponse:
    response = RedirectResponse(f"{_frontend()}/login?error", status_code=302)
    clear_oauth_state_cookie(response)
    return response


@router.get("/login/oauth2/code/google")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    auth: AuthService = Depends(get_auth_service),
    google: GoogleOAuthClient = Depends(get_google_client),
):
    expected = request.cookies.get(OAUTH_STATE_COOKIE)
    if error or not code or not state or not expected or not hmac.compare_digest(state, expected):
        logger.warning("Google OAuth callback rejected", extra={"oauth_error": error, "state_present": bool(state)})
        return _failure()
    try:
        info = await google.fetch_user(code)
        user = await auth.find_or_create_google_user(info.sub, info.email, info.name or info.email)
        pair = await auth.issue_tokens(user)
    except Exception:
        logger.exception("Google sign-in failed")
        return _failure()

    # The access token travels in the URL fragment, which is never sent to a server or kept in history.
    response = RedirectResponse(f"{_frontend()}/auth/callback#token={pair.auth_response.access_token}", status_code=302)
    set_refresh_cookie(response, pair.raw_refresh_token)
    clear_oauth_state_cookie(response)
    return response
