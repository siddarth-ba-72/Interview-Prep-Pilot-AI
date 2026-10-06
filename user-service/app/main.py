import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import create_client, ensure_index
from app.errors import register_exception_handlers
from app.logging_config import RequestIdMiddleware, setup_structured_logging
from app.repositories.refresh_tokens import RefreshTokensRepository
from app.repositories.users import UsersRepository
from app.routers import auth, oauth, users
from app.services.auth_service import AuthService
from app.services.google_oauth import GoogleOAuthClient
from app.services.jwt_service import JwtService
from app.services.user_service import UserService

setup_structured_logging("user-service", settings.log_level)


async def ensure_indexes(db) -> None:
    # The Java service never enabled auto-index-creation, so these may not exist yet (deviation D6).
    await ensure_index(db.users, "email", "email", unique=True)
    await ensure_index(db.users, "googleId", "googleId", unique=True, sparse=True)
    await ensure_index(db.refresh_tokens, "userId", "userId")
    await ensure_index(db.refresh_tokens, "expiresAt", "expiresAt", expireAfterSeconds=0)
    await ensure_index(db.refresh_tokens, "tokenHash", "tokenHash", unique=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Built first so a short JWT_SECRET stops the service before anything is opened.
    jwt_service = JwtService(settings.jwt_secret, settings.access_token_expiry_seconds)

    client = create_client()
    db = client[settings.mongodb_db]
    http = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    await ensure_indexes(db)

    users_repo = UsersRepository(db.users)
    app.state.mongo = client
    app.state.db = db
    app.state.http = http
    app.state.auth_service = AuthService(
        users_repo, RefreshTokensRepository(db.refresh_tokens), jwt_service, settings.refresh_token_expiry_days
    )
    app.state.user_service = UserService(users_repo)
    # redirect_uri is exactly what the Spring service used, so the Google console needs no change.
    app.state.google_client = GoogleOAuthClient(
        settings.google_client_id,
        settings.google_client_secret,
        f"{settings.frontend_origin.rstrip('/')}/login/oauth2/code/google",
        http,
    )
    yield
    await http.aclose()
    await client.close()


# redirect_slashes=False: a 307 here would point the browser at the internal host name.
app = FastAPI(title="PrepPilot User Service", lifespan=lifespan, redirect_slashes=False)
register_exception_handlers(app)
app.add_middleware(RequestIdMiddleware)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(users.router)


@app.get("/health")
async def health(request: Request):
    try:
        async with asyncio.timeout(2):
            await request.app.state.mongo.admin.command("ping")
    except Exception:
        return JSONResponse({"status": "down"}, status_code=503)
    return {"status": "ok"}
