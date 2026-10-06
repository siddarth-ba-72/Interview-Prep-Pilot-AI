from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.deps import get_auth_service
from app.errors import ApiError
from app.routers.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserProfile
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth")


@router.post("/register", status_code=201, response_model=UserProfile)
async def register(body: RegisterRequest, auth: AuthService = Depends(get_auth_service)):
    body.ensure_valid()
    return await auth.register(body)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, auth: AuthService = Depends(get_auth_service)):
    body.ensure_valid()
    pair = await auth.login(body)
    set_refresh_cookie(response, pair.raw_refresh_token)
    return pair.auth_response


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request, response: Response, auth: AuthService = Depends(get_auth_service)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw is None:
        raise ApiError(401, "INVALID_REFRESH_TOKEN", "Invalid or expired refresh token")
    pair = await auth.refresh(raw)
    set_refresh_cookie(response, pair.raw_refresh_token)
    return pair.auth_response


@router.post("/logout")
async def logout(request: Request, auth: AuthService = Depends(get_auth_service)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw is not None:
        await auth.logout(raw)
    response = Response(status_code=204)
    clear_refresh_cookie(response)
    return response


@router.get("/google", include_in_schema=False)
async def google_login():
    # Relative on purpose: the browser resolves it against whichever origin it reached us through.
    return RedirectResponse("/oauth2/authorization/google", status_code=302)
