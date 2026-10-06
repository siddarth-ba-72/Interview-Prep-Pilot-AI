from dataclasses import dataclass
from urllib.parse import unquote

from app.config import settings


@dataclass(frozen=True)
class Route:
    name: str
    prefixes: tuple[str, ...]
    upstream: str  # "user" or "topic"


# Evaluated in order; the first match wins. /api/v1/ai/** is deliberately absent (deviation D1):
# the UI never calls it and ai-service must only be reachable from topic-service.
ROUTES: tuple[Route, ...] = (
    Route("oauth2-routes", ("/oauth2", "/login/oauth2"), "user"),
    Route("auth-routes", ("/api/v1/auth",), "user"),
    Route("user-routes", ("/api/v1/users",), "user"),
    Route("topic-routes", ("/api/v1/topics", "/api/v1/sessions", "/api/v1/reports"), "topic"),
)

# Exactly Spring's startsWith whitelist. So "/api/v1/auth" with nothing after it is routed but not public.
PUBLIC_PREFIXES = ("/api/v1/auth/", "/oauth2/", "/login/oauth2/", "/health")


def _matches(path: str, prefix: str) -> bool:
    """Spring's Path=/x/** semantics."""
    return path == prefix or path.startswith(prefix + "/")


def match(path: str) -> Route | None:
    for route in ROUTES:
        if any(_matches(path, prefix) for prefix in route.prefixes):
            return route
    return None


def is_public(path: str) -> bool:
    return path.startswith(PUBLIC_PREFIXES)


def has_dot_segments(raw_path: str) -> bool:
    """True if any path segment is '.' or '..', in plain or percent-encoded form.

    Such a path could satisfy a public prefix here yet be normalised by the HTTP client into a protected
    one, so it is rejected outright. Browsers never send them.
    """
    return any(segment in (".", "..") for segment in unquote(raw_path).split("/"))


def upstream_base_url(route: Route) -> str:
    return settings.user_service_url if route.upstream == "user" else settings.topic_service_url
