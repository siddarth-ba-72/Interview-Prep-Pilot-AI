from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.errors import register_exception_handlers
from app.logging_config import RequestIdMiddleware, setup_structured_logging

setup_structured_logging("gateway", settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Same rule as JJWT: refuse to start with a short HMAC secret.
    if len(settings.jwt_secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 bytes")
    yield


# Docs are off so no generated route can shadow a proxied path.
app = FastAPI(title="PrepPilot Gateway", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
register_exception_handlers(app)
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
