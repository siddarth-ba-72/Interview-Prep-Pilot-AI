from fastapi import Header, HTTPException, status

from app.config import settings


async def require_caller_identity(
    x_internal_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    """Dual-auth: allow trusted internal callers (topic-service) or requests
    the Gateway has already authenticated via X-User-Id. Reject everything else."""
    if x_internal_api_key and settings.internal_api_key and x_internal_api_key == settings.internal_api_key:
        return "internal"
    if x_user_id:
        return x_user_id
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# Alias for convenience
async def require_internal_api_key_or_user_id(
    x_internal_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    """Dual-auth: allow trusted internal callers (topic-service) or requests
    the Gateway has already authenticated via X-User-Id. Reject everything else."""
    return await require_caller_identity(x_internal_api_key=x_internal_api_key, x_user_id=x_user_id)
