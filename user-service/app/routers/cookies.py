from fastapi import Response

from app.config import settings

REFRESH_COOKIE = "refresh_token"
# Kept identical to the Java service. Because of this path the browser never sends the cookie to
# /api/v1/auth/logout, so logout cannot revoke the token server-side (known issue K1, not fixed here).
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_PATH = "/login/oauth2"
OAUTH_STATE_MAX_AGE = 600


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expiry_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=None,  # not set, as in Java: the browser defaults to Lax
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, secure=settings.cookie_secure, httponly=True, samesite=None
    )


def set_oauth_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_MAX_AGE,
        path=OAUTH_STATE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        OAUTH_STATE_COOKIE, path=OAUTH_STATE_PATH, secure=settings.cookie_secure, httponly=True, samesite="lax"
    )
