from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import proxy
from app.auth import authenticate
from app.config import settings
from app.errors import ApiError, register_exception_handlers
from app.logging_config import RequestIdMiddleware, setup_structured_logging, user_id_context
from app.routes import has_dot_segments, is_public, match, upstream_base_url

setup_structured_logging("gateway", settings.log_level)

PROXIED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def create_app(
    user_transport: httpx.AsyncBaseTransport | None = None,
    topic_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Transports are injectable so tests can stand in for the upstream services."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Same rule as JJWT: refuse to start with a short HMAC secret.
        if len(settings.jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 bytes")
        app.state.clients = {
            "user": proxy.create_client(user_transport),
            "topic": proxy.create_client(topic_transport),
        }
        yield
        for client in app.state.clients.values():
            await client.aclose()

    # Docs are off so no generated route can shadow a proxied path.
    app = FastAPI(title="PrepPilot Gateway", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    register_exception_handlers(app)
    # Added last = outermost, so even the gateway's own 401/404/502 responses carry CORS headers
    # (otherwise the browser hides the 401 from axios and the silent refresh never fires).
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    # One catch-all, so auth happens in the handler (inside the CORS middleware) rather than in a middleware.
    @app.api_route("/{path:path}", methods=PROXIED_METHODS, include_in_schema=False)
    async def proxy_request(request: Request):
        raw_path = request.scope.get("raw_path")
        raw = raw_path.decode("latin-1") if raw_path else request.url.path
        path = request.url.path
        route = match(path)
        if route is None or has_dot_segments(raw):
            raise ApiError(404, "NOT_FOUND", "No route")

        extra: dict[str, str] = {}
        if not is_public(path):
            user_id, email = authenticate(request.headers.get("authorization"), settings.jwt_secret)
            user_id_context.set(user_id)
            extra = {"X-User-Id": user_id, "X-User-Email": email}

        client = request.app.state.clients[route.upstream]
        return await proxy.forward(request, client, upstream_base_url(route), extra)

    return app


app = create_app()
