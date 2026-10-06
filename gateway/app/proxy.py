import logging
import time

import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from app.config import settings
from app.errors import ApiError

logger = logging.getLogger(__name__)

HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

# Never trust these from a client: only the gateway may set X-User-*, and X-Internal-Api-Key is for
# service-to-service calls. Stripped on every route, public or not. host/content-length are recomputed
# by httpx; x-request-id is replaced with the gateway's own.
STRIPPED_REQUEST_HEADERS = HOP_BY_HOP | {
    "host",
    "content-length",
    "x-user-id",
    "x-user-email",
    "x-internal-api-key",
    "x-request-id",
}

# `date`/`server` would be duplicated by uvicorn; access-control-* belongs to the gateway's CORS layer alone.
SKIPPED_RESPONSE_HEADERS = HOP_BY_HOP | {"date", "server"}


def create_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    timeout = httpx.Timeout(connect=5, read=settings.upstream_read_timeout_seconds, write=30, pool=5)
    # Redirects are never followed: OAuth depends on 302s (and their Location) reaching the browser untouched.
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport)


def build_request_headers(request: Request, extra: dict[str, str]) -> list[tuple[str, str]]:
    headers = [
        (name.decode("latin-1"), value.decode("latin-1"))
        for name, value in request.headers.raw
        if name.decode("latin-1").lower() not in STRIPPED_REQUEST_HEADERS
    ]
    headers.extend(extra.items())
    headers.append(("X-Request-Id", request.state.request_id))
    return headers


def _skip_response_header(name: str) -> bool:
    lowered = name.lower()
    return lowered in SKIPPED_RESPONSE_HEADERS or lowered.startswith("access-control-")


async def forward(request: Request, client: httpx.AsyncClient, base_url: str, extra: dict[str, str]) -> Response:
    raw_path = request.scope.get("raw_path")
    path = raw_path.decode("latin-1") if raw_path else request.url.path
    query = request.scope.get("query_string", b"").decode("latin-1")
    url = f"{base_url}{path}" + (f"?{query}" if query else "")

    body = await request.body()  # request bodies here are small JSON
    upstream_request = client.build_request(
        request.method, url, headers=build_request_headers(request, extra), content=body or None
    )

    started = time.monotonic()
    try:
        upstream = await client.send(upstream_request, stream=True)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        logger.warning("Upstream unreachable", extra={"upstream": base_url, "path": path})
        raise ApiError(502, "UPSTREAM_UNAVAILABLE", "Upstream service unavailable") from None
    except httpx.TimeoutException:
        logger.warning("Upstream timed out", extra={"upstream": base_url, "path": path})
        raise ApiError(504, "UPSTREAM_TIMEOUT", "Upstream service timed out") from None
    except httpx.HTTPError:
        logger.warning("Upstream request failed", exc_info=True, extra={"upstream": base_url, "path": path})
        raise ApiError(502, "UPSTREAM_UNAVAILABLE", "Upstream service unavailable") from None

    logger.info(
        "Proxied request",
        extra={
            "method": request.method,
            "path": path,
            "upstream": base_url,
            "status": upstream.status_code,
            "upstream_ms": round((time.monotonic() - started) * 1000),
        },
    )

    async def body_stream():
        # Chunks are passed on as they arrive, which is what makes SSE work. Never read the whole body first.
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()

    response = StreamingResponse(body_stream(), status_code=upstream.status_code)
    # append, not a dict: there can be several Set-Cookie headers.
    for name, value in upstream.headers.multi_items():
        if not _skip_response_header(name):
            response.headers.append(name, value)
    return response
