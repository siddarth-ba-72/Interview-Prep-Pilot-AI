import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import create_client
from app.errors import register_exception_handlers
from app.logging_config import RequestIdMiddleware, setup_structured_logging

setup_structured_logging("user-service", settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Same rule as JJWT: refuse to start with a short HMAC secret.
    if len(settings.jwt_secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 bytes")
    client = create_client()
    app.state.mongo = client
    app.state.db = client[settings.mongodb_db]
    # Phase 2: ensure indexes and build the service singletons here.
    yield
    await client.close()


# redirect_slashes=False: a 307 here would point the browser at the internal host name.
app = FastAPI(title="PrepPilot User Service", lifespan=lifespan, redirect_slashes=False)
register_exception_handlers(app)
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health(request: Request):
    try:
        async with asyncio.timeout(2):
            await request.app.state.mongo.admin.command("ping")
    except Exception:
        return JSONResponse({"status": "down"}, status_code=503)
    return {"status": "ok"}
