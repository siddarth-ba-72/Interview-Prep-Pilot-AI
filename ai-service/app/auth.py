import secrets

from fastapi import Header, HTTPException, status

from app.config import settings


async def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    """Only topic-service may call this service; it sends the shared X-Internal-Api-Key.

    This service has a public URL and every call spends LLM tokens, so a bare X-User-Id
    header is not accepted: anyone can send one. Users reach the AI only through
    topic-service, which checks their access token and their usage limits first."""
    if not (
        settings.internal_api_key
        and x_internal_api_key
        and secrets.compare_digest(x_internal_api_key, settings.internal_api_key)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
